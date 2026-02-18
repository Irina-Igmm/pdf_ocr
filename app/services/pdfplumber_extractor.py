import io
import logging

import pdfplumber

logger = logging.getLogger(__name__)


def extract_text_pdfplumber(pdf_input) -> str:
    """Extract text from a PDF using pdfplumber.

    Args:
        pdf_input: file path (str), bytes, or file-like object.

    Returns:
        Concatenated text from all pages.
    """
    # Wrap raw bytes in a BytesIO so pdfplumber gets a seekable stream
    if isinstance(pdf_input, bytes):
        pdf_input = io.BytesIO(pdf_input)

    try:
        with pdfplumber.open(pdf_input) as pdf:
            pages_text = []
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if text.strip():
                    pages_text.append(f"--- Page {i + 1} ---\n{text}")
            return "\n\n".join(pages_text)
    except Exception as e:
        logger.warning("pdfplumber failed to parse PDF: %s", e)
        return ""