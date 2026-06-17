# Embeds a question and retrieves relevant chunks from ChromaDB.

import re
import time

import chromadb
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
        client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)
        _collection = client.get_or_create_collection(
            name=config.COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return _collection


# ── Code-query helpers ────────────────────────────────────────────────────────
_CODE_QUERY_RE = re.compile(
    r'\b(example|code|python|show|snippet|sample|demonstrate)\b', re.IGNORECASE
)
_CODE_CONTENT_RE = [
    re.compile(r'```'),
    re.compile(r'^\s{4}\S', re.MULTILINE),
    re.compile(r'\bdef \w+\s*\('),
    re.compile(r'\bimport \w+'),
    re.compile(r'\w+\.\w+\s*\('),
    re.compile(r'\[\s*[\d.\-]+\s*,'),
]


def _is_code_query(question: str) -> bool:
    """True if the question seeks a code example."""
    return bool(_CODE_QUERY_RE.search(question))


def _chunk_has_code(text: str) -> bool:
    """True if the chunk appears to contain a code block."""
    return any(p.search(text) for p in _CODE_CONTENT_RE)


# ── Definition-intent helpers ─────────────────────────────────────────────────
# Detect queries like "What is X", "What are X", "Define X", "Explain X".
_DEF_QUERY_RE = re.compile(
    r'^(?:what\s+(?:is|are)\s+(?:an?\s+)?|define\s+|explain\s+)(.+?)[\?]?\s*$',
    re.IGNORECASE,
)

# Vague/stop terms that should NOT trigger definition-intent scoring.
_DEF_STOP_TERMS = frozenset({
    "more", "this", "it", "that", "they", "them", "these", "those",
    "the", "difference", "differences", "everything", "anything", "something",
})


def _extract_def_term(question: str) -> str | None:
    """Return the queried concept for definition-style questions, else None."""
    m = _DEF_QUERY_RE.match(question.strip())
    if not m:
        return None
    term = m.group(1).strip().rstrip('?').strip()
    term = re.sub(r'^the\s+', '', term, flags=re.IGNORECASE).strip()
    if len(term) < 3 or term.lower() in _DEF_STOP_TERMS:
        return None
    return term


def _term_pattern(term: str) -> str:
    """Build a regex fragment matching the term and its simple singular/plural form."""
    t = re.escape(term.lower())
    if term.lower().endswith('s'):
        # Already plural — also match without trailing 's'
        singular = re.escape(term.lower()[:-1])
        return rf'(?:{t}|{singular})'
    else:
        # Singular — also match with trailing 's'
        return rf'{t}s?'


def _chunk_defines_term(text: str, term: str) -> bool:
    """True if the chunk contains a definitional sentence pattern for the term."""
    lower = text.lower()
    tp = _term_pattern(term)
    patterns = [
        rf'\b{tp}\s+(?:is|are)\b',           # "container is", "containers are"
        rf'\ban?\s+{tp}\s+is\b',              # "a container is", "an image is"
        rf'\b{tp}:\s',                          # "container: ..."
        rf'what\s+(?:is|are)\s+(?:an?\s+)?{tp}\b',  # "what is a container"
    ]
    return any(re.search(p, lower) for p in patterns)


def _chunk_mentions_incidentally(text: str, term: str) -> bool:
    """True if the term appears only in comparison/marketing/deployment context."""
    lower = text.lower()
    tp = _term_pattern(term)
    patterns = [
        rf'alternative\s+to\s+(?:[\w-]+\s+)*{tp}',          # "alternative to VMs"
        rf'compar\w*\s+(?:to|with)\s+(?:[\w-]+\s+)*{tp}',   # "compared to VMs"
        rf'instead\s+of\s+(?:[\w-]+\s+)*{tp}',               # "instead of VMs"
        rf'(?:run|runs|running)\s+on\s+(?:[\w-]+\s+)*{tp}',  # "running on VMs"
        rf'(?:unlike|versus|vs\.?)\s+(?:[\w-]+\s+)*{tp}',   # "versus VMs"
    ]
    return any(re.search(p, lower) for p in patterns)


# Public API.
def retrieve(document_id: str, question: str) -> tuple:
    """Returns (chunks, sources, best_score, refused). Raw question always used for embedding."""
    log.info(
        f"Retrieval started — document_id={document_id}  "
        f"retrieval_query={question!r:.80}  (raw user question — no history injected)"
    )

    model = _model_get()
    col   = _collection_get()

    t0    = time.time()
    q_vec = model.encode([question], normalize_embeddings=True).tolist()

    try:
        results = col.query(
            query_embeddings = q_vec,
            n_results        = config.TOP_K,
            where            = {"document_id": document_id},
            include          = ["documents", "distances", "metadatas"],
        )
    except Exception:
        log.exception(f"ChromaDB query failed for document_id={document_id}")
        raise

    elapsed = time.time() - t0

    docs      = results["documents"][0] if results["documents"] else []
    distances = results["distances"][0]  if results["distances"]  else []
    metas     = results["metadatas"][0]  if results["metadatas"]   else []

    if not docs:
        log.warning(f"No chunks found for document_id={document_id} — document may not be ingested")
        return [], [], 0.0, True

    scores = [1.0 - d for d in distances]

    # Log all scores — distribution is needed for threshold/margin tuning.
    all_scores_str = "  ".join(f"{s:.3f}" for s in scores)
    log.info(
        f"Chunk scores [{len(scores)}]: [{all_scores_str}]  "
        f"best={max(scores):.3f}  threshold={config.SIMILARITY_THRESHOLD}"
    )

    # Boost score of code-containing chunks on code-seeking queries.
    if _is_code_query(question):
        boosted_count = sum(1 for d in docs if _chunk_has_code(d))
        scores = [
            min(1.0, s + config.CODE_SCORE_BOOST) if _chunk_has_code(doc) else s
            for s, doc in zip(scores, docs)
        ]
        log.debug(
            f"Code query — boosted {boosted_count}/{len(docs)} code chunks "
            f"by +{config.CODE_SCORE_BOOST}"
        )

    # Definition-intent scoring — runs after code boost, before threshold gate.
    # For "What is X" / "Define X" / "Explain X" queries:
    #   1. If NO chunk defines the term → refuse immediately (semantic match ≠ definitional match).
    #   2. If definitions exist → boost them; penalise incidental-mention chunks.
    def_term = _extract_def_term(question)
    if def_term is not None:
        adjusted = []
        has_def  = False
        for doc, score in zip(docs, scores):
            if _chunk_defines_term(doc, def_term):
                adjusted.append(min(1.0, score + config.DEFINITION_BOOST))
                has_def = True
            elif _chunk_mentions_incidentally(doc, def_term):
                adjusted.append(max(0.0, score - config.MENTION_PENALTY))
            else:
                adjusted.append(score)
        scores = adjusted

        if not has_def:
            # No chunk contains a definitional sentence for the queried term.
            # Return a refusal — semantic similarity to mentions is not sufficient.
            sources = [
                {
                    "similarity": round(score, 4),
                    "preview":    text[:200].replace("\n", " ").strip(),
                    "url":        meta.get("url", ""),
                    "sent_to_llm": False,
                }
                for text, score, meta in zip(docs, scores, metas)
            ]
            log.warning(
                f"RETRIEVAL RESULT — refused=True  reason=no_definition_chunk  "
                f"term={def_term!r}  scores=[{'  '.join(f'{s:.3f}' for s in scores)}]  "
                f"latency={elapsed:.3f}s"
            )
            return [], sources, max(scores) if scores else 0.0, True

        log.info(
            f"Definition query — term={def_term!r}  has_definition=True  "
            f"adjusted_scores=[{'  '.join(f'{s:.3f}' for s in scores)}]"
        )

    best_score = max(scores)

    log.info(
        f"Retrieval latency={elapsed:.3f}s — "
        f"{len(docs)} chunks returned, best_score={best_score:.3f}, threshold={config.SIMILARITY_THRESHOLD}"
    )

    # Gate 1a: hard refuse — scores below STRICT_REFUSAL_THRESHOLD mean no topical overlap.
    if best_score < config.STRICT_REFUSAL_THRESHOLD:
        sources = [
            {
                "similarity": round(score, 4),
                "preview":    text[:200].replace("\n", " ").strip(),
                "url":        meta.get("url", ""),
                "sent_to_llm": False,
            }
            for text, score, meta in zip(docs, scores, metas)
        ]
        log.warning(
            f"RETRIEVAL RESULT — refused=True  reason=below_strict_threshold  "
            f"best={best_score:.3f}  strict_threshold={config.STRICT_REFUSAL_THRESHOLD}  "
            f"all_scores=[{all_scores_str}]  latency={elapsed:.3f}s"
        )
        return [], sources, best_score, True

    # Gate 2: drop chunks scoring more than PROXIMITY_MARGIN below the best.
    proximity_floor = best_score - config.PROXIMITY_MARGIN

    sources = [
        {
            "similarity":  round(score, 4),
            "preview":     text[:200].replace("\n", " ").strip(),
            "url":         meta.get("url", ""),
            "sent_to_llm": score >= proximity_floor,
        }
        for text, score, meta in zip(docs, scores, metas)
    ]

    llm_chunks = [
        doc for doc, score in zip(docs, scores)
        if score >= proximity_floor
    ]

    if not llm_chunks:
        log.warning(
            f"RETRIEVAL RESULT — refused=True  reason=proximity_filter  "
            f"all_chunks_below_floor  floor={proximity_floor:.3f}  "
            f"best={best_score:.3f}  all_scores=[{all_scores_str}]  latency={elapsed:.3f}s"
        )
        return [], sources, best_score, True

    log.info(
        f"RETRIEVAL RESULT — refused=False  "
        f"chunks_to_llm={len(llm_chunks)}/{len(docs)}  best={best_score:.3f}  "
        f"all_scores=[{all_scores_str}]  floor={proximity_floor:.3f}  latency={elapsed:.3f}s"
    )
    return llm_chunks, sources, best_score, False


if __name__ == "__main__":
    doc_id   = input("Paste document_id from pipeline.py: ").strip()
    question = "How do you create a FastAPI application?"
    chunks, sources, score, refused = retrieve(doc_id, question)
    print(f"\nRefused: {refused}  Best score: {score:.3f}  Chunks: {len(chunks)}")
    for s in sources:
        print(f"\n  [{s['similarity']}] {s['preview'][:120]}...")
