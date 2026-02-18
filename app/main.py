from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.routers.receipt import router as receipt_router

app = FastAPI(
    title="Receipt OCR API",
    description=(
        "Extract structured information from scanned PDF receipts.\n\n"
        "Powered by Groq Cloud LLM (qwen3-32b / gpt-oss-120b), "
        "EasyOCR, PaddleOCR, and Unstructured (Tesseract)."
    ),
    version="1.0.0",
)

app.include_router(receipt_router)


@app.get("/health", include_in_schema=False)
async def health():
    """Health check endpoint used by Docker HEALTHCHECK."""
    return JSONResponse({"status": "ok"})
