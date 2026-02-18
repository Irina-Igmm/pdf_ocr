from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI

from app.routers.receipt import router as receipt_router

app = FastAPI(
    title="Receipt OCR API",
    description="Extract structured information from scanned PDF receipts using EasyOCR.",
    version="1.0.0",
)

app.include_router(receipt_router)
