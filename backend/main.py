from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import chat, ingest, sessions
from backend.logging.logger import get_logger

log = get_logger(__name__)

app = FastAPI(
    title="Documentation Q&A API",
    description="Ingest documentation URLs and ask grounded questions about them.",
    version="1.0.0",
)

# CORS — the React/Vite frontend (default ports 5173/3000) calls this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)
app.include_router(chat.router)
app.include_router(sessions.router)


@app.get("/", summary="Health check")
def health():
    """Simple liveness probe."""
    return {"status": "ok", "service": "Documentation Q&A API"}


log.info("FastAPI app initialized — routers: ingest, chat, sessions")
