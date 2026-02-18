"""DEPRECATED — Ollama is no longer used.

This module exists only as a backward-compatible shim. All LLM calls
now go through Groq. If any code still imports ``chat_completion``
from here, it will be routed to the Groq client with the default model.
"""

import logging
import os

from app.services.groq_client import GroqLLMClient

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = os.getenv("LLM_MODEL", "qwen/qwen3-32b")
_default_client = GroqLLMClient(_DEFAULT_MODEL)


def chat_completion(
    system_prompt: str,
    user_prompt: str,
    *,
    model: str | None = None,
    temperature: float = 0.1,
) -> str:
    """Backward-compatible wrapper — delegates to GroqLLMClient."""
    client = GroqLLMClient(model) if model else _default_client
    return client.chat_completion(
        system_prompt, user_prompt, temperature=temperature
    )
