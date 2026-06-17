# Loads recent messages from SQLite and formats them as a prompt prefix for the LLM.

from backend.logging.logger import get_logger
from backend.memory.sqlite_store import load_recent_messages

log = get_logger(__name__)


def format_history_for_prompt(messages: list[dict]) -> str:
    # Formats {role, content} dicts into a 'Previous conversation:' text block.
    if not messages:
        return ""
    lines = []
    for m in messages:
        prefix = "User" if m["role"] == "user" else "Assistant"
        lines.append(f"{prefix}: {m['content']}")
    return "Previous conversation:\n" + "\n".join(lines) + "\n\n"


def load_and_format_history(session_id: str, limit: int = 5) -> str:
    # Loads the last `limit` turns from SQLite and returns them as a prompt prefix.
    messages = load_recent_messages(session_id, limit=limit)
    log.info(f"[2] History loaded — {len(messages)} messages from SQLite (session {session_id})")
    return format_history_for_prompt(messages)
