# SQLite store for sessions, messages, and documents. DB file: <project root>/memory.db

import sqlite3
from pathlib import Path

_DB_PATH = Path(__file__).parent.parent.parent / "memory.db"


# Connection factory — new connection per call, WAL mode for concurrency.
def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


# Schema + Session CRUD.
def init_db() -> None:
    """Create tables if they don't exist.  Safe to call on every startup."""
    conn = _connect()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id         TEXT PRIMARY KEY,
                title      TEXT,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT    NOT NULL REFERENCES sessions(id),
                role       TEXT    NOT NULL CHECK(role IN ('user','assistant')),
                content    TEXT    NOT NULL,
                created_at TEXT    DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id);

            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT PRIMARY KEY,
                url         TEXT NOT NULL,
                created_at  TEXT DEFAULT (datetime('now'))
            );
        """)
        # Migrate existing databases that pre-date the updated_at column.
        try:
            conn.execute("ALTER TABLE sessions ADD COLUMN updated_at TEXT")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # column already exists
    finally:
        conn.close()


def create_session(session_id: str, title: str | None = None) -> dict:
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO sessions(id, title, updated_at) VALUES(?, ?, datetime('now'))",
            (session_id, title),
        )
        conn.commit()
        return get_session(session_id)  # type: ignore[return-value]
    finally:
        conn.close()


def get_session(session_id: str) -> dict | None:
    conn = _connect()
    try:
        row = conn.execute(
            """
            SELECT s.id, s.title, s.created_at, s.updated_at,
                   COUNT(m.id) AS message_count
            FROM sessions s
            LEFT JOIN messages m ON m.session_id = s.id
            WHERE s.id = ?
            GROUP BY s.id
            """,
            (session_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_sessions() -> list[dict]:
    conn = _connect()
    try:
        rows = conn.execute(
            """
            SELECT s.id, s.title, s.created_at, s.updated_at,
                   COUNT(m.id) AS message_count
            FROM sessions s
            LEFT JOIN messages m ON m.session_id = s.id
            GROUP BY s.id
            ORDER BY COALESCE(s.updated_at, s.created_at) DESC
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_session_title(session_id: str, title: str) -> dict | None:
    """Rename a session's title.  Returns updated session or None if not found."""
    conn = _connect()
    try:
        conn.execute(
            "UPDATE sessions SET title = ? WHERE id = ?",
            (title, session_id),
        )
        conn.commit()
    finally:
        conn.close()
    return get_session(session_id)


def delete_session(session_id: str) -> None:
    """Delete a session and all its messages (manual cascade)."""
    conn = _connect()
    try:
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()


# Message CRUD.
def save_message(session_id: str, role: str, content: str) -> None:
    conn = _connect()
    try:
        conn.execute(
            "INSERT INTO messages(session_id, role, content) VALUES(?, ?, ?)",
            (session_id, role, content),
        )
        # Touch updated_at on every new message.
        conn.execute(
            "UPDATE sessions SET updated_at = datetime('now') WHERE id = ?",
            (session_id,),
        )
        # Auto-title: first user message sets the session title (max 50 chars).
        if role == "user":
            conn.execute(
                "UPDATE sessions SET title = ? WHERE id = ? AND title IS NULL",
                (content[:50], session_id),
            )
        conn.commit()
    finally:
        conn.close()


def get_messages(session_id: str) -> list[dict]:
    """Return all messages for a session in chronological order."""
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT id, session_id, role, content, created_at "
            "FROM messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def load_recent_messages(session_id: str, limit: int = 5) -> list[dict]:
    """
    Load the most recent `limit` conversation turns (user + assistant pairs)
    and return them in chronological order.
    Called by history.py to build the context prefix for the LLM.
    """
    conn = _connect()
    try:
        rows = conn.execute(
            "SELECT role, content FROM messages "
            "WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
            (session_id, limit * 2),
        ).fetchall()
        return [dict(r) for r in reversed(rows)]
    finally:
        conn.close()


# Document CRUD.
def upsert_document(document_id: str, url: str) -> None:
    """Track an ingested document.  Idempotent — safe to call on re-ingest."""
    conn = _connect()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO documents(document_id, url) VALUES(?, ?)",
            (document_id, url),
        )
        conn.commit()
    finally:
        conn.close()


# Initialise DB on import — creates tables if not present.
init_db()
