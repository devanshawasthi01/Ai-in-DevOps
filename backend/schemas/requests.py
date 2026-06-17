# Pydantic request models for /ingest and /chat routes.

from typing import Optional

from pydantic import BaseModel


class IngestRequest(BaseModel):
    url: str


class ChatRequest(BaseModel):
    document_id: str
    question: str
    session_id: Optional[str] = None  # Pass to enable conversation memory.
