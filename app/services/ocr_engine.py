"""OCR engine facade — delegates to the backend selected by the OCR_BACKEND env var.

Supported values for OCR_BACKEND:
  easyocr    (default) — uses EasyOCR
  paddleocr             — uses PaddleOCR (requires paddlepaddle + paddleocr installed)
"""

import logging
import os

from app.services.base_ocr import BaseOCRExtractor

# Re-export for backward compatibility with any code that imports COUNTRY_TO_LANGS
# directly from this module.
from app.services.easyocr_tool import _EASYOCR_COUNTRY_TO_LANGS as COUNTRY_TO_LANGS

logger = logging.getLogger(__name__)


def _load_backend() -> BaseOCRExtractor:
    backend = os.environ.get("OCR_BACKEND", "easyocr").lower().strip()
    if backend == "easyocr":
        from app.services.easyocr_tool import EasyOCRTool
        logger.info("OCR backend: EasyOCR")
        return EasyOCRTool()
    if backend == "paddleocr":
        from app.services.paddleocr_tool import PaddleOCRTool
        logger.info("OCR backend: PaddleOCR")
        return PaddleOCRTool()
    if backend == "unstructured":
        from app.services.unstructured_tool import UnstructuredTool
        logger.info("OCR backend: Unstructured (Tesseract)")
        return UnstructuredTool()
    raise ValueError(
        f"Unknown OCR_BACKEND value: {backend!r}. "
        "Supported values: 'easyocr', 'paddleocr', 'unstructured'."
    )


# Module-level singleton — instantiated once on first import.
_backend: BaseOCRExtractor = _load_backend()


def extract_text(
    image,
    lang_list: list[str] | None = None,
    country_code: str | None = None,
) -> str:
    """Run OCR on an image (or list of images) and return extracted text.

    Delegates to the backend selected by the OCR_BACKEND environment variable
    (default: 'easyocr'). Signature is identical to the original function.

    Args:
        image: PIL Image, numpy array, file path, bytes,
               or a list of any of the above (multi-page PDF).
        lang_list: Backend-specific language codes.
        country_code: Dataset country code (e.g. "de", "fr") used to
                      infer languages when lang_list is not provided.
    """
    return _backend.extract_text(image, lang_list=lang_list, country_code=country_code)
