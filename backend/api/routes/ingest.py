# POST /ingest — fetch a URL, chunk it, embed it, store in ChromaDB.

from fastapi import APIRouter, HTTPException

from backend.ingestion import pipeline
from backend.logging.logger import get_logger
from backend.memory import sqlite_store
from backend.schemas.requests import IngestRequest

log = get_logger(__name__)

router = APIRouter()


@router.post("/ingest", summary="Ingest a documentation URL")
def route_ingest(req: IngestRequest):
    """Fetches URL → extracts text → chunks → embeds → stores in ChromaDB. Returns document_id."""
    try:
        log.info(f"Ingest request — url={req.url}")
        result = pipeline.ingest(req.url)
    except ValueError as e:
        log.warning(f"Ingest validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        log.exception("Ingest error in route_ingest")
        raise HTTPException(status_code=500, detail=str(e))

    # Record document in SQLite (non-blocking — ChromaDB ingest already succeeded).
    try:
        sqlite_store.upsert_document(result["document_id"], req.url)
    except Exception:
        log.warning("Could not record document in memory.db — ignoring")

    return result
