# Full ingestion pipeline: URL → text → chunks → embeddings → ChromaDB.

import hashlib
import re
import time

import chromadb
import httpx
import trafilatura
from bs4 import BeautifulSoup
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

from backend.config import settings as config
from backend.logging.logger import get_logger

log = get_logger(__name__)

# Singletons — lazy-loaded on first use.
_model      = None
_collection = None


def _model_get():
    global _model
    if _model is None:
        log.info(f"Loading embedding model: {config.EMBEDDING_MODEL}")
        _model = SentenceTransformer(config.EMBEDDING_MODEL)
        log.info("Embedding model loaded")
    return _model


def _collection_get():
    global _collection
    if _collection is None:
        log.info(f"Connecting to ChromaDB at {config.CHROMA_PERSIST_DIR}")
        client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)
        _collection = client.get_or_create_collection(
            name=config.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        log.info(f"Collection '{config.COLLECTION_NAME}' ready")
    return _collection


# ── Pipeline steps ─────────────────────────────────────────────────────────────

def _fetch(url: str) -> str:
    log.info(f"Fetching URL: {url}")
    t0 = time.time()
    resp = httpx.get(
        url,
        timeout=30,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (compatible; DocBot/1.0)"},
    )
    resp.raise_for_status()
    elapsed = time.time() - t0
    log.info(f"Fetch complete in {elapsed:.2f}s — {len(resp.text):,} chars of HTML")
    return resp.text


def _extract_code_blocks(html: str) -> str:
    """Extracts code blocks from Shiki-rendered HTML where trafilatura sees no code."""
    soup = BeautifulSoup(html, "lxml")
    blocks = []
    for el in soup.find_all("code", attrs={"language": True}):
        lang = el.get("language", "python")
        lines = el.find_all("span", class_="line")
        code_text = "\n".join(l.get_text() for l in lines) if lines else el.get_text()
        code_text = code_text.strip()
        if len(code_text) >= 10:
            blocks.append(f"```{lang}\n{code_text}\n```")
    return "\n\n".join(blocks)


def _extract(html: str) -> str:
    log.debug("Extracting text with trafilatura")
    prose = trafilatura.extract(
        html,
        include_comments=False,
        include_tables=True,
        include_formatting=True,
    )

    # Append code blocks missed by trafilatura on Shiki-rendered pages.
    code_text = _extract_code_blocks(html)
    if code_text:
        n_blocks = code_text.count("```") // 2
        log.debug(f"BeautifulSoup extracted {n_blocks} code block(s) ({len(code_text)} chars)")

    if prose and code_text:
        text = prose.strip() + "\n\n" + code_text
    elif prose:
        text = prose
    else:
        text = code_text

    if text and len(text) > 300:
        log.info(f"Extracted {len(text):,} chars (prose={len(prose) if prose else 0}, code={len(code_text) if code_text else 0})")
        return text

    log.warning("Extraction insufficient — using full BeautifulSoup fallback")
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)
    if len(text) < 100:
        raise ValueError("Could not extract meaningful text from this URL.")
    log.info(f"BeautifulSoup fallback extracted {len(text):,} chars")
    return text


# Patterns to detect code in chunks.
_CODE_CHUNK_RE = [
    re.compile(r'```'),
    re.compile(r'^\s{4}\S', re.MULTILINE),
    re.compile(r'\bdef \w+\s*\('),
    re.compile(r'\bimport \w+'),
    re.compile(r'\w+\.\w+\s*\('),          # method calls: collection.add(
    re.compile(r'\[\s*[\d.\-]+\s*,'),      # array literals: [1.1, 2.3,
]

# Separators ordered to avoid splitting mid-code-block.
_CODE_AWARE_SEPARATORS = ["\n\n", "\n```", "```\n", "\n", " ", ""]


def _has_code(text: str) -> bool:
    """Return True when the chunk appears to contain a code block."""
    return any(p.search(text) for p in _CODE_CHUNK_RE)


def _chunk(text: str, document_id: str, url: str) -> list:
    log.debug(f"Chunking text ({len(text):,} chars, size={config.CHUNK_SIZE}, overlap={config.CHUNK_OVERLAP})")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=_CODE_AWARE_SEPARATORS,
    )
    pieces = splitter.split_text(text)
    if not pieces:
        raise ValueError("Chunking produced 0 chunks — document may be too short.")
    code_count = sum(1 for p in pieces if _has_code(p))
    log.info(f"Created {len(pieces)} chunks ({code_count} contain code)")
    return [
        {
            "id":          f"{document_id}_{i}",
            "text":        piece,
            "document_id": document_id,
            "url":         url,
            "has_code":    _has_code(piece),
        }
        for i, piece in enumerate(pieces)
    ]


def _embed_store(chunks: list) -> None:
    model = _model_get()
    col   = _collection_get()
    texts = [c["text"] for c in chunks]
    log.info(f"Encoding {len(texts)} chunks")
    t0   = time.time()
    vecs = model.encode(texts, normalize_embeddings=True).tolist()
    log.info(f"Embedding complete in {time.time() - t0:.2f}s")
    log.debug("Upserting vectors into ChromaDB")
    col.upsert(
        ids        = [c["id"] for c in chunks],
        embeddings = vecs,
        documents  = texts,
        metadatas  = [
            {"document_id": c["document_id"], "url": c["url"], "has_code": int(c.get("has_code", False))}
            for c in chunks
        ],
    )
    log.info(f"Upserted {len(chunks)} chunks into ChromaDB")


# Public API.
def ingest(url: str) -> dict:
    """Ingest a URL end-to-end. Returns document_id, chunk count, and url."""
    t_start     = time.time()
    document_id = hashlib.sha256(url.encode()).hexdigest()[:16]
    log.info(f"Ingest started — document_id={document_id}  url={url}")
    try:
        html   = _fetch(url)
        text   = _extract(html)
        chunks = _chunk(text, document_id, url)
        _embed_store(chunks)
    except Exception:
        log.exception(f"Ingest FAILED for url={url}")
        raise
    elapsed = time.time() - t_start
    log.info(f"Ingest complete in {elapsed:.2f}s — {len(chunks)} chunks stored")
    return {"document_id": document_id, "chunks_count": len(chunks), "url": url}


if __name__ == "__main__":
    url    = "https://fastapi.tiangolo.com/tutorial/first-steps/"
    result = ingest(url)
    print(f"\nResult: {result}")
    print(f"  document_id = \"{result['document_id']}\"")
