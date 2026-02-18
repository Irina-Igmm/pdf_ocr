import logging
import os
from functools import lru_cache

import numpy as np
from PIL import Image

from app.services.base_ocr import BaseOCRExtractor

# Disable OneDNN (MKL-DNN) to avoid compatibility crashes on Windows/some CPUs
os.environ["FLAGS_use_mkldnn"] = "0"
os.environ["MKLDNN_CACHE_CAPACITY"] = "0"
os.environ["PADDLE_DISABLE_MKLDNN"] = "1"

logger = logging.getLogger(__name__)

# PaddleOCR language codes differ from EasyOCR codes.
# Reference: https://paddlepaddle.github.io/PaddleOCR/main/en/ppocr/blog/multi_languages.html
_PADDLE_COUNTRY_TO_LANGS: dict[str, list[str]] = {
    "de": ["german", "en"],
    "at": ["german", "en"],
    "us": ["en"],
    "uk": ["en"],
    "fr": ["fr", "en"],
    "es": ["es", "en"],
    "nl": ["nl", "en"],
    "ca": ["en", "fr"],
    "cn": ["ch", "en"],           # Simplified Chinese
    "hk": ["chinese_cht", "en"],  # Traditional Chinese
    "ee": ["en"],                  # Estonian not supported; fallback to English
    # Lithuanian not supported; fallback to English
    "lt": ["en"],
    "se": ["en"],                  # Swedish not supported; fallback to English
    "pl": ["en"],                  # Polish not supported; fallback to English
    "hr": ["en"],                  # Croatian not supported; fallback to English
    "gr": ["en"],                  # Greek not supported
    "ir": ["en"],                  # Ireland
    "cz": ["en"],                  # Czech not supported; fallback to English
    "be": ["fr", "en"],
}


def _to_numpy(image) -> np.ndarray:
    """Convert a single image to a numpy array compatible with PaddleOCR."""
    if isinstance(image, np.ndarray):
        return image
    if isinstance(image, Image.Image):
        return np.array(image)
    raise ValueError(
        f"Unsupported image type for PaddleOCR: {type(image)}. "
        "Expected PIL.Image or numpy array."
    )


@lru_cache(maxsize=8)
def _get_reader(lang: str):
    """Create and cache a PaddleOCR instance (keyed by language)."""
    try:
        from paddleocr import PaddleOCRVL
    except ImportError as exc:
        raise RuntimeError(
            "PaddleOCR is not installed. "
            "Install it with: pip install paddlepaddle paddleocr"
        ) from exc
    logger.info("Initializing PaddleOCR reader for language: %s", lang)

    return PaddleOCRVL()

def _ocr_single(reader, image) -> str:
    """Run PaddleOCR on a single image and return extracted text."""
    img_array = _to_numpy(image)
    try:
        result = reader.ocr(img_array, cls=True)
    except RuntimeError as exc:
        msg = str(exc)
        if "OneDnn" in msg or "mkldnn" in msg.lower() or "fused_conv2d" in msg:
            raise RuntimeError(
                "PaddleOCR crashed due to an OneDNN/MKL-DNN incompatibility "
                "on this platform.  Switch to the EasyOCR backend by setting "
                "the environment variable OCR_BACKEND=easyocr (in your .env "
                "file or system environment)."
            ) from exc
        raise
    lines = []
    if result:
        for block in result:
            if block:
                for line in block:
                    text = line[1][0]
                    lines.append(text)
    return "\n".join(lines)


class PaddleOCRTool(BaseOCRExtractor):
    """OCR backend using PaddleOCR."""

    @property
    def backend_name(self) -> str:
        return "paddleocr"

    def extract_text(
        self,
        image,
        lang_list: list[str] | None = None,
        country_code: str | None = None,
    ) -> str:
        if lang_list is None and country_code is not None:
            lang_list = _PADDLE_COUNTRY_TO_LANGS.get(
                country_code.lower(), ["en"])
        if lang_list is None:
            lang_list = ["en"]

        # PaddleOCR uses one primary language per reader instance.
        primary_lang = lang_list[0] if lang_list else "en"
        reader = _get_reader(primary_lang)

        if isinstance(image, list):
            parts = []
            for i, img in enumerate(image):
                page_text = _ocr_single(reader, img)
                if page_text.strip():
                    parts.append(f"--- Page {i + 1} ---\n{page_text}")
            return "\n\n".join(parts)

        return _ocr_single(reader, image)
