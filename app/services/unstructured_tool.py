"""OCR backend using unstructured.partition.pdf.

Leverages the `unstructured` library to extract text from scanned PDFs
with built-in OCR support and multilanguage handling via Tesseract.
"""

import logging
import tempfile
import os
import shutil
from typing import Union

# Configure Tesseract on Windows for unstructured
if os.name == "nt":
    # Common default install paths
    possible_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        os.environ.get("TESSERACT_CMD", ""),
    ]
    for path in possible_paths:
        if path and os.path.exists(path):
            try:
                import unstructured_pytesseract
                unstructured_pytesseract.pytesseract.tesseract_cmd = path
                break
            except ImportError:
                pass


from app.services.base_ocr import BaseOCRExtractor, ImageInput

logger = logging.getLogger(__name__)

# Map ISO country codes to Tesseract language codes used by unstructured
_UNSTRUCTURED_COUNTRY_TO_LANGS: dict[str, list[str]] = {
    "de": ["deu", "eng"],
    "at": ["deu", "eng"],
    "us": ["eng"],
    "uk": ["eng"],
    "fr": ["fra", "eng"],
    "es": ["spa", "eng"],
    "nl": ["nld", "eng"],
    "ca": ["eng", "fra"],
    "cn": ["chi_sim", "eng"],
    "hk": ["chi_tra", "eng"],
    "ee": ["est", "eng"],
    "lt": ["lit", "eng"],
    "se": ["swe", "eng"],
    "pl": ["pol", "eng"],
    "hr": ["hrv", "eng"],
    "gr": ["ell", "eng"],
    "ir": ["fas", "eng"],
    "cz": ["ces", "eng"],
    "be": ["fra", "nld", "eng"],
    "it": ["ita", "eng"],
    "pt": ["por", "eng"],
    "ro": ["ron", "eng"],
    "hu": ["hun", "eng"],
    "bg": ["bul", "eng"],
    "ru": ["rus", "eng"],
    "tr": ["tur", "eng"],
}


def _extract_from_pdf_bytes(
    pdf_bytes: bytes,
    languages: list[str] | None = None,
) -> str:
    """Run unstructured partition_pdf on raw PDF bytes.

    Args:
        pdf_bytes: Raw PDF file content.
        languages: Tesseract language codes (e.g. ["fra", "eng"]).
                   Defaults to ["eng"] if not provided.

    Returns:
        Extracted text as a single string with page delimiters.
    """
    from unstructured.partition.pdf import partition_pdf

    if not languages:
        languages = ["eng"]

    # unstructured needs a file on disk; write to a temp file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(pdf_bytes)
        tmp_path = tmp.name

    try:
        elements = partition_pdf(
            filename=tmp_path,
            strategy="ocr_only",
            ocr_languages="+".join(languages),
        )
    finally:
        import os
        os.unlink(tmp_path)

    # Group elements by page number and format output
    pages: dict[int, list[str]] = {}
    for el in elements:
        page_num = el.metadata.page_number or 1
        text = str(el).strip()
        if text:
            pages.setdefault(page_num, []).append(text)

    if not pages:
        return ""

    parts: list[str] = []
    for page_num in sorted(pages):
        page_text = "\n".join(pages[page_num])
        parts.append(f"--- Page {page_num} ---\n{page_text}")

    return "\n\n".join(parts)


class UnstructuredTool(BaseOCRExtractor):
    """OCR backend using unstructured.partition.pdf with Tesseract OCR.

    This backend is designed for scanned/image PDFs and supports
    multilanguage documents via Tesseract language packs.

    Note: Unlike other OCR backends that work on pre-rendered images,
    this backend works best when given the raw PDF bytes directly.
    When used via the image-based interface (extract_text with images),
    it converts images back to a temporary PDF for processing.
    """

    @property
    def backend_name(self) -> str:
        return "unstructured"

    def extract_text(
        self,
        image: Union[ImageInput, "list[ImageInput]"],
        lang_list: list[str] | None = None,
        country_code: str | None = None,
    ) -> str:
        # Resolve language list from country code
        if lang_list is None and country_code is not None:
            lang_list = _UNSTRUCTURED_COUNTRY_TO_LANGS.get(
                country_code.lower(), ["eng"]
            )
        if lang_list is None:
            lang_list = ["eng"]

        # If we received raw PDF bytes, use them directly
        if isinstance(image, bytes):
            return _extract_from_pdf_bytes(image, languages=lang_list)

        # For PIL images or numpy arrays, convert to a temporary PDF
        from PIL import Image
        import numpy as np

        images_list = image if isinstance(image, list) else [image]

        pil_images: list[Image.Image] = []
        for img in images_list:
            if isinstance(img, Image.Image):
                pil_images.append(img.convert("RGB"))
            elif isinstance(img, np.ndarray):
                pil_images.append(Image.fromarray(img).convert("RGB"))
            elif isinstance(img, str):
                pil_images.append(Image.open(img).convert("RGB"))
            elif isinstance(img, bytes):
                # Could be raw PDF bytes for a single page
                return _extract_from_pdf_bytes(img, languages=lang_list)
            else:
                raise ValueError(f"Unsupported image type: {type(img)}")

        if not pil_images:
            return ""

        # Save all images as a multi-page PDF and process
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_path = tmp.name
            pil_images[0].save(
                tmp_path,
                "PDF",
                save_all=True,
                append_images=pil_images[1:] if len(pil_images) > 1 else [],
                resolution=300,
            )

        try:
            return _extract_from_pdf_bytes(
                open(tmp_path, "rb").read(), languages=lang_list
            )
        finally:
            import os
            os.unlink(tmp_path)

    def extract_from_pdf(
        self,
        pdf_bytes: bytes,
        lang_list: list[str] | None = None,
        country_code: str | None = None,
    ) -> str:
        """Extract text directly from PDF bytes (preferred method).

        This avoids the PDF→image→PDF round-trip and gives better results.
        """
        if lang_list is None and country_code is not None:
            lang_list = _UNSTRUCTURED_COUNTRY_TO_LANGS.get(
                country_code.lower(), ["eng"]
            )
        if lang_list is None:
            lang_list = ["eng"]

        return _extract_from_pdf_bytes(pdf_bytes, languages=lang_list)
