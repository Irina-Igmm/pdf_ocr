"""Hybrid receipt parser — pdfplumber + EasyOCR + Ollama (qwen2.5).

Combines text extracted by pdfplumber (native text layer) with EasyOCR
(image-based OCR) to build a richer input, then sends the merged text
to Ollama for structured JSON extraction.
"""

import logging

from app.schemas.receipt import ReceiptResponse
from app.services.json_utils import RECEIPT_SCHEMA_PROMPT, parse_json_response
from app.services.ocr_engine import extract_text
from app.services.ollama_client import chat_completion
from app.services.pdf_converter import pdf_to_images
from app.services.pdfplumber_extractor import extract_text_pdfplumber

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "Given text extracted from a scanned receipt using two methods "
    "(pdfplumber for native text and EasyOCR for image-based OCR), "
    + RECEIPT_SCHEMA_PROMPT
)


class HybridReceiptParser:
    """Merge pdfplumber + EasyOCR text, then parse via Ollama."""

    def parse(self, pdf_bytes: bytes) -> ReceiptResponse:
        # 1. Extract native text via pdfplumber
        plumber_text = extract_text_pdfplumber(pdf_bytes)

        # 2. Extract OCR text via EasyOCR on rendered images
        images = pdf_to_images(pdf_bytes)
        ocr_text = extract_text(images)

        # 3. Merge both sources
        merged = self._merge_texts(plumber_text, ocr_text)

        if not merged.strip():
            logger.warning("Hybrid: no text extracted from either source")
            return parse_json_response("")

        # 4. Send to Ollama
        raw = chat_completion(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=f"Parse this receipt:\n\n{merged}",
        )
        logger.info("Ollama (hybrid) raw response: %s", raw[:300])
        return parse_json_response(raw)

    @staticmethod
    def _merge_texts(plumber_text: str, ocr_text: str) -> str:
        """Combine pdfplumber and EasyOCR outputs into a single prompt."""
        parts: list[str] = []

        if plumber_text.strip():
            parts.append(
                "=== Text extracted by pdfplumber (native text layer) ===\n"
                + plumber_text
            )

        if ocr_text.strip():
            parts.append(
                "=== Text extracted by EasyOCR (image-based OCR) ===\n"
                + ocr_text
            )

        return "\n\n".join(parts)
