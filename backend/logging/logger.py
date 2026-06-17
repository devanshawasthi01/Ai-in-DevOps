# Centralised logger: console (INFO+) and app.log (DEBUG+). Call get_logger(__name__) in any module.

import logging  # stdlib; no shadowing — backend.logging is a sub-package, not top-level
import sys
from pathlib import Path

_LOG_FILE   = Path(__file__).parent.parent.parent / "app.log"  # project root
_FMT        = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FMT   = "%Y-%m-%d %H:%M:%S"
_configured = False


def _configure() -> None:
    global _configured
    if _configured:
        return

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    fmt = logging.Formatter(_FMT, datefmt=_DATE_FMT)

    # Console handler — INFO and above
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    root.addHandler(ch)

    # File handler — DEBUG and above
    fh = logging.FileHandler(_LOG_FILE, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # Silence noisy third-party loggers
    for noisy in ("httpx", "httpcore", "urllib3", "huggingface_hub",
                  "sentence_transformers", "chromadb", "watchfiles"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a named logger. Configures root logger on first call."""
    _configure()
    return logging.getLogger(name)
