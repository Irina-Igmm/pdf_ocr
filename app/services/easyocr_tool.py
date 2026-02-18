import logging
from functools import lru_cache

import numpy as np
from PIL import Image

from app.services.base_ocr import BaseOCRExtractor

logger = logging.getLogger(__name__)

CYRILLIC_LANGS = {"ru", "rs_cyrillic", "be", "bg", "uk", "mn"}
LATIN_LANGS = {
    "en", "fr", "de", "es", "it", "pt", "nl", "pl", "cs", "ro", "hr",
    "sk", "sl", "sq", "tr", "vi", "id", "ms", "tl", "sw", "af", "az",
    "bs", "ca", "cy", "da", "et", "fi", "ga", "hu", "is", "la", "lt",
    "lv", "mt", "no", "oc", "sv", "uz", "eu", "mi",
}

_EASYOCR_COUNTRY_TO_LANGS: dict[str, list[str]] = {
    "de": ["de", "en"],
    "at": ["de", "en"],
    "us": ["en"],
    "uk": ["en"],
    "fr": ["fr", "en"],
    "es": ["es", "en"],
    "nl": ["nl", "en"],
    "ca": ["en", "fr"],
    "cn": ["ch_sim", "en"],
    "hk": ["ch_tra", "en"],
    "ee": ["et", "en"],
    "lt": ["lt", "en"],
    "se": ["sv", "en"],
    "pl": ["pl", "en"],
    "hr": ["hr", "en"],
    "gr": ["en"],
    "ir": ["en"],
    "cz": ["cs", "en"],
    "be": ["fr", "nl", "en"],
}


def _validate_lang_list(lang_list: list[str]) -> list[str]:
    """Validate and fix language list to avoid EasyOCR compatibility errors."""
    has_cyrillic = any(lang in CYRILLIC_LANGS for lang in lang_list)
    has_latin_non_en = any(
        lang in LATIN_LANGS and lang != "en" for lang in lang_list
    )

    if has_cyrillic and has_latin_non_en:
        filtered = [
            lang for lang in lang_list if lang in CYRILLIC_LANGS or lang == "en"
        ]
        if not filtered:
            filtered = ["en"]
        logger.warning(
            "Incompatible lang_list %s — filtered to %s (Cyrillic + English only)",
            lang_list,
            filtered,
        )
        return filtered

    if "en" not in lang_list:
        lang_list = [*lang_list, "en"]

    return lang_list


def _to_numpy(image) -> np.ndarray:
    """Convert a single image to a numpy array compatible with EasyOCR."""
    if isinstance(image, np.ndarray):
        return image
    if isinstance(image, Image.Image):
        return np.array(image)
    if isinstance(image, (str, bytes)):
        return image
    raise ValueError(
        f"Unsupported image type: {type(image)}. "
        "Expected PIL.Image, numpy array, file path (str), or bytes."
    )


@lru_cache(maxsize=8)
def _get_reader(lang_tuple: tuple[str, ...]):
    """Create and cache an EasyOCR Reader (keyed by language tuple)."""
    import easyocr
    logger.info("Initializing EasyOCR reader for languages: %s", lang_tuple)
    return easyocr.Reader(list(lang_tuple), gpu=False)


class EasyOCRTool(BaseOCRExtractor):
    """OCR backend using EasyOCR."""

    @property
    def backend_name(self) -> str:
        return "easyocr"

    def extract_text(
        self,
        image,
        lang_list: list[str] | None = None,
        country_code: str | None = None,
    ) -> str:
        if lang_list is None and country_code is not None:
            lang_list = _EASYOCR_COUNTRY_TO_LANGS.get(country_code.lower(), ["en"])
        if lang_list is None:
            lang_list = ["en"]

        lang_list = _validate_lang_list(lang_list)
        lang_tuple = tuple(sorted(set(lang_list)))
        reader = _get_reader(lang_tuple)

        if isinstance(image, list):
            parts = []
            for i, img in enumerate(image):
                results = reader.readtext(_to_numpy(img), detail=0)
                page_text = "\n".join(results)
                if page_text.strip():
                    parts.append(f"--- Page {i + 1} ---\n{page_text}")
            return "\n\n".join(parts)

        results = reader.readtext(_to_numpy(image), detail=0)
        return "\n".join(results)
