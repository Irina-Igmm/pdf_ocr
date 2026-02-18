"""Hybrid receipt parser — pdfplumber + OCR + LLM.

Combines text extracted by pdfplumber (native text layer) with OCR
(image-based) to build a richer input, then sends the merged text
to an LLM for structured JSON extraction.
"""

import logging

from app.schemas.receipt import ReceiptResponse
from app.services.base_llm import BaseLLMClient
from app.services.json_utils import RECEIPT_SCHEMA_PROMPT, parse_json_response
from app.services.ocr_engine import extract_text
from app.services.pdf_converter import pdf_to_images
from app.services.pdfplumber_extractor import extract_text_pdfplumber

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Given text extracted from a scanned receipt using two methods "
    "(pdfplumber for native text and OCR for image-based recognition), "
    + RECEIPT_SCHEMA_PROMPT
)


class HybridReceiptParser:
    """Merge pdfplumber + OCR text, then parse via LLM."""

    def __init__(self, *, llm_client: BaseLLMClient | None = None):
        if llm_client is None:
            from app.services.groq_client import GroqLLMClient
            llm_client = GroqLLMClient("qwen/qwen3-32b")
        self._llm = llm_client

    def parse(self, pdf_bytes: bytes) -> ReceiptResponse:
        # 1. Extract native text via pdfplumber
        plumber_text = extract_text_pdfplumber(pdf_bytes)

        # 2. Extract OCR text on rendered images
        images = pdf_to_images(pdf_bytes)
        ocr_text = extract_text(images)

        # 3. Merge both sources
        merged = self._merge_texts(plumber_text, ocr_text)

        if not merged.strip():
            logger.warning("Hybrid: no text extracted from either source")
            return parse_json_response("")

        # 4. Send to LLM
        raw = self._llm.chat_completion(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=f"Parse this receipt:\n\n{merged}",
        )
        logger.info("LLM (%s) hybrid raw response: %s", self._llm.backend_name, raw[:300])
        return parse_json_response(raw)

    @staticmethod
    def _merge_texts(plumber_text: str, ocr_text: str) -> str:
        """Combine pdfplumber and OCR outputs into a single prompt."""
        parts: list[str] = []

        if plumber_text.strip():
            parts.append(
                "=== Text extracted by pdfplumber (native text layer) ===\n"
                + plumber_text
            )

        if ocr_text.strip():
            parts.append(
                "=== Text extracted by OCR (image-based) ===\n"
                + ocr_text
            )

        return "\n\n".join(parts)
