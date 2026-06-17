# Calls Ollama phi3 with retrieved context chunks and returns the grounded answer.

import time

import httpx

from backend.config import settings as config
from backend.logging.logger import get_logger
from backend.llm.prompts import _SYSTEM

log = get_logger(__name__)


def ask(context_chunks: list, question: str) -> str:
    """Sends context chunks + question to Ollama. Returns the grounded answer string."""

    context = "\n\n---\n\n".join(context_chunks)
    log.info(f"[5] LLM started — model={config.OLLAMA_MODEL}  chunks={len(context_chunks)}  question={question!r:.60}")

    t0 = time.time()
    resp = httpx.post(
        f"{config.OLLAMA_BASE_URL}/api/chat",

        json={
            "model": config.OLLAMA_MODEL,

            "stream": False,

            "options": {
                "temperature":    0.1,   # slight stochasticity reduces rigid refusal phrasing
                "top_p":          0.9,   # nucleus sampling — filters low-probability tokens
                "repeat_penalty": 1.1,   # reduces repetition without distorting factual content
                "num_predict":    300,   # concise answers (~200-250 words)
            },

            "messages": [

                {
                    "role": "system",
                    "content": _SYSTEM
                },

                {
                    "role": "user",
                    "content":
f"""Documentation:
{context}

Question: {question}

Answer using only the documentation above."""
                }

            ],
        },

        timeout=config.OLLAMA_TIMEOUT,
    )

    try:
        resp.raise_for_status()
    except Exception:
        log.exception("Ollama request failed")
        raise
    elapsed = time.time() - t0

    answer = resp.json()["message"]["content"].strip()
    log.info(f"[6] LLM completed — {config.OLLAMA_MODEL} responded in {elapsed:.1f}s  answer={len(answer)} chars")
    return answer


if __name__ == "__main__":

    print("Testing Ollama connection...\n")

    sample_chunks = [

        """
FastAPI is a modern Python framework.

Run development server:

fastapi dev main.py

Example:

from fastapi import FastAPI

app = FastAPI()
        """

    ]

    question = "How do I run FastAPI?"

    answer = ask(sample_chunks, question)

    print("Question:")
    print(question)

    print("\nAnswer:")
    print(answer)
