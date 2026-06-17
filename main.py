# FastAPI entrypoint — registers all routers.

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import chat, ingest, sessions

app = FastAPI(
    title="Talk to the Docs — MVP",
    description="Ingest a URL then ask questions. Answers come only from the document.",
    version="0.1.0",
)

# CORS: allow React dev server on both localhost and 127.0.0.1 (IPv6 mismatch fix).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(ingest.router)
app.include_router(chat.router)
app.include_router(sessions.router)
