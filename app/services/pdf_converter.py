import fitz  # PyMuPDF
from PIL import Image
import io


def pdf_to_images(pdf_bytes: bytes, dpi: int = 300) -> list[Image.Image]:
    """Convert each page of a PDF to a PIL Image at the given DPI."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)

    for page in doc:
        pix = page.get_pixmap(matrix=matrix)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        images.append(img)

    doc.close()
    return images
