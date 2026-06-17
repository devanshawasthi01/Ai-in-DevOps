# ── LLM ──────────────────────────────────────────────────────────────────────
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "phi3:latest"
OLLAMA_TIMEOUT = 180


# ── Embeddings ────────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# ── ChromaDB ──────────────────────────────────────────────────────────────────
CHROMA_PERSIST_DIR = "./chroma_db_mvp"
COLLECTION_NAME    = "doc-chunks"

# ── Chunking ──────────────────────────────────────────────────────────────────
# 400 chars ≈ 3-4 sentences — one concept per chunk reduces topic contamination.
CHUNK_SIZE    = 400
# ~20% overlap (80/400) preserves meaning at chunk boundaries.
CHUNK_OVERLAP = 80

# ── Retrieval ─────────────────────────────────────────────────────────────────
# 4 candidates: balanced diversity without adding noise from low-scoring chunks.
TOP_K = 4

# Single refusal threshold — weak-match zone eliminated for strict grounded QA.
# Anything below 0.30 is a hard refuse; no "maybe related" answering.
STRICT_REFUSAL_THRESHOLD = 0.30

# Must equal STRICT_REFUSAL_THRESHOLD — both gates unified at one threshold.
SIMILARITY_THRESHOLD = 0.30

CODE_SCORE_BOOST = 0.15    # score boost for code chunks on code-seeking queries
PROXIMITY_MARGIN = 0.08    # tighter filter: only chunks within 0.08 of best survive

DEFINITION_BOOST  = 0.08   # additive boost for chunks that define the queried concept
MENTION_PENALTY   = 0.05   # additive penalty for chunks that only mention the concept incidentally

# ── Memory ────────────────────────────────────────────────────────────────────
# 3 user + 3 assistant = 6 messages. load_recent_messages uses LIMIT (limit*2),
# so pass MAX_MEMORY_MESSAGES // 2 as the turns argument.
# More than 3 turns risks polluting the LLM prompt and degrading retrieval focus.
MAX_MEMORY_MESSAGES = 6


if __name__ == "__main__":
    print(f"Model:      {OLLAMA_MODEL}")
    print(f"Embeddings: {EMBEDDING_MODEL}")
    print(f"Chunk size: {CHUNK_SIZE}")
    print(f"Threshold:  {SIMILARITY_THRESHOLD}")
