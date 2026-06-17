# POST /chat — retrieves relevant chunks then asks the LLM to answer from them.

import time

from fastapi import APIRouter, HTTPException

from backend.config import settings as config
from backend.llm import ollama, validator
from backend.logging.logger import get_logger
from backend.memory import sqlite_store
from backend.memory.history import load_and_format_history
from backend.retrieval import search
from backend.schemas.requests import ChatRequest

log = get_logger(__name__)

router = APIRouter()


@router.post("/chat", summary="Ask a question about an ingested document")
def route_chat(req: ChatRequest):
    """Retrieve → LLM → validate → return answer. Pass session_id for conversation memory."""
    t0_request = time.time()
    log.info(f"Chat request — document_id={req.document_id}  question={req.question!r:.80}")

    # effective_question adds history for the LLM; raw req.question is always used for retrieval.
    effective_question = req.question

    if req.session_id is not None:
        if sqlite_store.get_session(req.session_id) is None:
            raise HTTPException(
                status_code=404,
                detail=f"Session '{req.session_id}' not found. "
                       "Create one via POST /sessions/create.",
            )
        log.info(f"[1] Session validated — {req.session_id}")
        history_text = load_and_format_history(req.session_id, limit=config.MAX_MEMORY_MESSAGES // 2)
        if history_text:
            effective_question = history_text + "Current question: " + req.question
            log.info(f"[2] History injected — {len(effective_question)} chars effective prompt")
        else:
            log.info("[2] History loaded — 0 messages (first turn)")

    # Retrieval always uses raw question — never diluted by history.
    try:
        chunks, sources, score, refused = search.retrieve(req.document_id, req.question)
    except Exception as e:
        log.exception("Retrieval error in route_chat")
        raise HTTPException(status_code=500, detail=str(e))

    log.info(f"[3] Retrieval — {len(chunks)} chunks  score={score:.3f}  prompt_chars={len(effective_question)}")

    if refused:
        log.info(f"Refused — score={score:.3f}  total_latency={time.time()-t0_request:.3f}s")
        return {
            "answer":  "I cannot find this information in the provided documentation.",
            "refused": True,
            "score":   round(score, 4),
            "sources": sources,
        }

    # LLM call — effective_question includes history when session is active.
    context_chars = sum(len(c) for c in chunks)
    log.info(f"[4] Prompt size — question={len(effective_question)} chars  context={context_chars} chars  total={len(effective_question)+context_chars} chars")
    try:
        answer = ollama.ask(chunks, effective_question)
    except Exception as e:
        log.exception("LLM error in route_chat")
        raise HTTPException(status_code=500, detail=str(e))

    # Post-generation validation.
    is_valid, violated_phrase = validator.validate(answer)
    if not is_valid:
        log.error(
            f"Validation failed — forbidden phrase '{violated_phrase}' in answer; "
            f"returning refusal (session={req.session_id}, score={score:.3f})"
        )
        return {
            "answer":            "I cannot find this information in the provided documentation.",
            "refused":           True,
            "score":             round(score, 4),
            "sources":           sources,
            "validation_failed": True,
        }

    # Persist only on grounded, validated answers.
    if req.session_id is not None:
        try:
            sqlite_store.save_message(req.session_id, "user", req.question)
            sqlite_store.save_message(req.session_id, "assistant", answer)
            log.info(f"[7] Messages saved — user + assistant written to SQLite (session {req.session_id})")
        except Exception:
            log.exception("Failed to persist messages — answer still returned")

    log.info(f"Chat complete — score={score:.3f}  chunks_used={len(chunks)}  total_latency={time.time()-t0_request:.3f}s")
    return {
        "answer":      answer,
        "refused":     False,
        "score":       round(score, 4),
        "chunks_used": len(chunks),
        "sources":     sources,
    }