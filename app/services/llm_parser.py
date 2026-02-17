"""LLM receipt parser — OCR text → JSON via Ollama (qwen2.5)."""

import logging

from app.schemas.receipt import ReceiptResponse
from app.services.json_utils import RECEIPT_SCHEMA_PROMPT, parse_json_response
from app.services.ollama_client import chat_completion

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Given raw OCR text from a scanned receipt, " + RECEIPT_SCHEMA_PROMPT
)


class LlmReceiptParser:
    """Parse raw OCR text into structured receipt data via Ollama."""

    def parse(self, raw_text: str) -> ReceiptResponse:
        raw = chat_completion(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=f"Parse this receipt:\n\n{raw_text}",
        )
        logger.info("Ollama (LLM) raw response: %s", raw[:300])
        return parse_json_response(raw)
