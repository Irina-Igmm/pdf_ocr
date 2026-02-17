"""Shared Ollama client for all LLM parsers.

Centralises access to the local Ollama instance running ``qwen2.5:latest``.
Every parser calls :func:`chat_completion` instead of managing its own
client / API key.

Environment variables
---------------------
``OLLAMA_BASE_URL``  – Ollama server URL (default ``http://localhost:11434``).
``OLLAMA_MODEL``     – Model tag to use   (default ``qwen2.5:latest``).
"""

import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:latest")


def _get_client():
    """Return a configured :class:`ollama.Client`."""
    import ollama

    return ollama.Client(host=OLLAMA_BASE_URL)


def chat_completion(
    system_prompt: str,
    user_prompt: str,
    *,
    model: str | None = None,
    temperature: float = 0.1,
) -> str:
    """Send a system + user message to Ollama and return the raw text.

    Args:
        system_prompt: The system instruction (role, format, examples).
        user_prompt:   The actual receipt text / data.
        model:         Override the default model if needed.
        temperature:   Sampling temperature (low = deterministic).

    Returns:
        The assistant's reply as a plain string.
    """
    client = _get_client()
    target_model = model or OLLAMA_MODEL

    logger.info("Ollama: sending request to %s (model=%s)",
                OLLAMA_BASE_URL, target_model)

    response = client.chat(
        model=target_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        options={"temperature": temperature},
    )

    text: str = response["message"]["content"]
    logger.info("Ollama raw response (%d chars): %s", len(text), text[:300])
    return text
