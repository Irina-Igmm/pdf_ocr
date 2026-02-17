import logging
from functools import lru_cache

import easyocr
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

CYRILLIC_LANGS = {"ru", "rs_cyrillic", "be", "bg", "uk", "mn"}
LATIN_LANGS = {
    "en", "fr", "de", "es", "it", "pt", "nl", "pl", "cs", "ro", "hr",
    "sk", "sl", "sq", "tr", "vi", "id", "ms", "tl", "sw", "af", "az",
    "bs", "ca", "cy", "da", "et", "fi", "ga", "hu", "is", "la", "lt",
    "lv", "mt", "no", "oc", "sv", "uz", "eu", "mi",
}

# Mapping from dataset country codes to EasyOCR language codes
COUNTRY_TO_LANGS: dict[str, list[str]] = {
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
    "gr": ["en"],          # EasyOCR does not support Greek script well; fallback to English
    "ir": ["en"],           # Ireland
    "cz": ["cs", "en"],
    "be": ["fr", "nl", "en"],
}


def _validate_lang_list(lang_list: list[str]) -> list[str]:
    """
    Validate and fix language list to avoid EasyOCR compatibility errors.
    Cyrillic languages can only be combined with English.
    """
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


@lru_cache(maxsize=8)
def _get_reader(lang_tuple: tuple[str, ...]) -> easyocr.Reader:
    """Create and cache an EasyOCR Reader (keyed by language tuple)."""
    logger.info("Initializing EasyOCR reader for languages: %s", lang_tuple)
    return easyocr.Reader(list(lang_tuple), gpu=False)


def _to_numpy(image) -> np.ndarray:
    """Convert a single image to a numpy array compatible with EasyOCR."""
    if isinstance(image, np.ndarray):
        return image
    if isinstance(image, Image.Image):
        return np.array(image)
    if isinstance(image, (str, bytes)):
        # Already a format EasyOCR accepts natively
        return image
    raise ValueError(
        f"Unsupported image type: {type(image)}. "
        "Expected PIL.Image, numpy array, file path (str), or bytes."
    )


def extract_text(
    image,
    lang_list: list[str] | None = None,
    country_code: str | None = None,
) -> str:
    """Run OCR on an image (or list of images) and return extracted text.

    Args:
        image: PIL Image, numpy array, file path, bytes,
            or a **list** of any of the above (multi-page PDF).
        lang_list: Explicit EasyOCR language codes.
        country_code: Dataset country code (e.g. "de", "fr") — used to
            infer languages when *lang_list* is not provided.
    """
    if lang_list is None and country_code is not None:
        lang_list = COUNTRY_TO_LANGS.get(country_code.lower(), ["en"])
    if lang_list is None:
        lang_list = ["en"]

    lang_list = _validate_lang_list(lang_list)
    lang_tuple = tuple(sorted(set(lang_list)))

    reader = _get_reader(lang_tuple)

    # Handle list of images (multi-page PDF)
    if isinstance(image, list):
        all_text_parts = []
        for i, img in enumerate(image):
            img_input = _to_numpy(img)
            results = reader.readtext(img_input, detail=0)
            page_text = "\n".join(results)
            if page_text.strip():
                all_text_parts.append(f"--- Page {i + 1} ---\n{page_text}")
        return "\n\n".join(all_text_parts)

    # Single image
    img_input = _to_numpy(image)
    results = reader.readtext(img_input, detail=0)
    return "\n".join(results)