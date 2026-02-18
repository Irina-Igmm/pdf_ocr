"""LLM receipt parser — OCR text → JSON via an LLM backend."""

import logging

from app.schemas.receipt import ReceiptResponse
from app.services.base_llm import BaseLLMClient
from app.services.json_utils import RECEIPT_SCHEMA_PROMPT, parse_json_response

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Given raw OCR text from a scanned receipt, " + RECEIPT_SCHEMA_PROMPT
)


class LlmReceiptParser:
    """Parse raw OCR text into structured receipt data via an LLM."""

    def __init__(self, *, llm_client: BaseLLMClient | None = None):
        if llm_client is None:
            from app.services.groq_client import GroqLLMClient
            llm_client = GroqLLMClient("qwen/qwen3-32b")
        self._llm = llm_client

    def parse(self, raw_text: str) -> ReceiptResponse:
        raw = self._llm.chat_completion(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=f"Parse this receipt:\n\n{raw_text}",
        )
        logger.info("LLM (%s) raw response: %s", self._llm.backend_name, raw[:300])
        return parse_json_response(raw)
