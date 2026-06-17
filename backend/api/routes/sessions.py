# Session CRUD routes — create, list, get, rename, delete.

import uuid
from typing import Optional

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

from backend.logging.logger import get_logger
from backend.memory import sqlite_store

log = get_logger(__name__)

router = APIRouter(prefix="/sessions", tags=["sessions"])


# ── Request schemas ────────────────────────────────────────────────────────────

class SessionCreateRequest(BaseModel):
    title: Optional[str] = None


class SessionRenameRequest(BaseModel):
    title: str


# ── Helper ───────────────────────────────────────────────────────────────────────

def _get_or_404(session_id: str) -> dict:
    sess = sqlite_store.get_session(session_id)
    if sess is None:
        raise HTTPException(status_code=404, detail=f"Session '{session_id}' not found.")
    return sess


# ── Routes ───────────────────────────────────────────────────────────────────────

@router.post("/create", summary="Create a new session")
def create_session(req: Optional[SessionCreateRequest] = Body(default=None)):
    """Creates a session and returns its id. Title auto-set from first question if omitted."""
    session_id = str(uuid.uuid4())
    title = req.title if req is not None else None
    sess = sqlite_store.create_session(session_id, title)
    log.info(f"Created session {session_id!r}  title={title!r}")
    return sess


@router.get("", summary="List all sessions")
def list_sessions():
    """Returns all sessions ordered by most recently active."""
    return sqlite_store.get_sessions()


@router.get("/{session_id}/messages", summary="Get chat history for a session")
def get_messages(session_id: str):
    """Returns full message history (role + content) in chronological order."""
    _get_or_404(session_id)
    return sqlite_store.get_messages(session_id)


@router.get("/{session_id}", summary="Get session metadata")
def get_session(session_id: str):
    """Returns id, title, created_at, updated_at, message_count for a session."""
    return _get_or_404(session_id)


@router.patch("/{session_id}", summary="Rename a session")
def rename_session(session_id: str, req: SessionRenameRequest):
    """Updates the session title. Returns the updated session object."""
    _get_or_404(session_id)
    updated = sqlite_store.update_session_title(session_id, req.title.strip())
    log.info(f"Renamed session {session_id!r} → {req.title!r}")
    return updated


@router.delete("/{session_id}", summary="Delete a session and its messages")
def delete_session(session_id: str):
    """Permanently deletes the session and all its messages."""
    _get_or_404(session_id)
    sqlite_store.delete_session(session_id)
    log.info(f"Deleted session {session_id!r}")
    return {"deleted": True, "session_id": session_id}
