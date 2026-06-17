# Post-generation hallucination check. Scans LLM answer for speculation phrases.

from backend.logging.logger import get_logger

log = get_logger(__name__)

# High-signal speculation phrases only.
# Excluded common technical-doc vocabulary that must NOT cause false refusals:
#   likely / generally / usually / typically / normally
# These appear frequently in legitimate documentation and are safe to quote.
_FORBIDDEN = [
    # "likely" excluded — appears verbatim in technical docs
    "probably",
    "possibly",
    "implied",
    "inferred",
    "can be inferred",
    "it can be assumed",
    "logically",
    "would suggest",
    "it is expected",
    "this suggests",
    "based on common",
]


def validate(answer: str) -> tuple:
    """Returns (is_valid, violated_phrase). Rejects answers containing speculation phrases."""
    lower = answer.lower()
    for phrase in _FORBIDDEN:
        if phrase in lower:
            log.error(
                f"Validator rejected answer — forbidden speculation phrase detected: '{phrase}' "
                f"— answer preview: {answer[:120]!r}"
            )
            return False, phrase
    return True, ""
