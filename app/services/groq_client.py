"""Groq Cloud LLM client — uses the official groq SDK with Langfuse tracing."""

import logging
import os

from app.services.base_llm import BaseLLMClient

logger = logging.getLogger(__name__)

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")

# Langfuse config (read from env / .env)
LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
LANGFUSE_BASE_URL: str = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")


def _get_langfuse():
    """Return a Langfuse client if credentials are configured, else None."""
    if not LANGFUSE_SECRET_KEY or not LANGFUSE_PUBLIC_KEY:
        return None
    try:
        from langfuse import Langfuse
        return Langfuse(
            secret_key=LANGFUSE_SECRET_KEY,
            public_key=LANGFUSE_PUBLIC_KEY,
            host=LANGFUSE_BASE_URL,
        )
    except ImportError:
        logger.debug("langfuse not installed — tracing disabled")
        return None


class GroqLLMClient(BaseLLMClient):
    """LLM backend using Groq Cloud."""

    def __init__(self, model: str):
        self._model = model

    @property
    def backend_name(self) -> str:
        return f"groq:{self._model}"

    def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        temperature: float = 0.1,
    ) -> str:
        from groq import Groq

        if not GROQ_API_KEY:
            raise RuntimeError(
                "GROQ_API_KEY is not set. "
                "Set it in your .env file or environment variables."
            )

        client = Groq(api_key=GROQ_API_KEY)
        langfuse = _get_langfuse()

        logger.info("Groq: sending request (model=%s)", self._model)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        # Start Langfuse trace if available (v3 API)
        generation = None
        if langfuse:
            generation = langfuse.start_generation(
                name="chat",
                model=self._model,
                input=messages,
                metadata={"source": "pdf_ocr"},
                model_parameters={
                    "temperature": str(temperature),
                    "max_completion_tokens": 8192,
                },
            )

        # reasoning_effort is only supported by qwen models on Groq
        extra_params = {}
        if "qwen" in self._model.lower():
            extra_params["reasoning_effort"] = "none"

        completion = client.chat.completions.create(
            model=self._model,
            messages=messages,
            temperature=temperature,
            max_completion_tokens=8192,
            top_p=1,
            stop=None,
            **extra_params,
        )

        text: str = completion.choices[0].message.content or ""

        # End Langfuse generation with usage stats (v3 API)
        if generation:
            usage = completion.usage
            generation.update(
                output=text,
                usage_details={
                    "input": usage.prompt_tokens if usage else 0,
                    "output": usage.completion_tokens if usage else 0,
                    "total": usage.total_tokens if usage else 0,
                },
            )
            generation.end()

        if langfuse:
            langfuse.flush()

        logger.info("Groq raw response (%d chars): %s", len(text), text[:300])
        return text
