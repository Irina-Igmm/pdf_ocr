from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.schemas.receipt import BatchReceiptResponse, BatchReceiptResult, ReceiptResponse
from app.services.ocr_engine import extract_text
from app.services.parser_factory import (
    IMAGE_STRATEGIES,
    PDF_BYTES_STRATEGIES,
    ParsingStrategy,
    get_parser,
)
from app.services.pdf_converter import pdf_to_images

import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Receipt OCR"])


@router.post(
    "/process_pdf",
    response_model=ReceiptResponse,
    response_model_by_alias=True,
    response_model_exclude_none=True,
    summary="Extract structured data from a scanned PDF receipt",
)
async def process_pdf(
    file: UploadFile = File(...),
    strategy: ParsingStrategy = Query(
        default=ParsingStrategy.HYBRID,
        description=(
            "Parsing strategy: 'regex', 'llm', 'gemini', or 'hybrid'. "
            "'hybrid' uses pdfplumber + EasyOCR + Ollama."
        ),
    ),
) -> ReceiptResponse:
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    parser = get_parser(strategy)

    # Strategies that handle PDF bytes internally (pdfplumber-based)
    if strategy in PDF_BYTES_STRATEGIES:
        return parser.parse(pdf_bytes)

    images = pdf_to_images(pdf_bytes)

    # Strategies that work directly on images (Gemini multimodal)
    if strategy in IMAGE_STRATEGIES:
        return parser.parse(images)

    # Text-based strategies (regex, llm) — need EasyOCR first
    raw_text = extract_text(images)

    if not raw_text.strip():
        raise HTTPException(status_code=422, detail="No text could be extracted from the PDF.")

    return parser.parse(raw_text)


@router.post(
    "/process_batch",
    response_model=BatchReceiptResponse,
    response_model_by_alias=True,
    response_model_exclude_none=True,
    summary="Extract structured data from multiple PDF receipts",
)
async def process_batch(
    files: list[UploadFile] = File(..., description="One or more PDF files to process"),
    strategy: ParsingStrategy = Query(
        default=ParsingStrategy.HYBRID,
        description=(
            "Parsing strategy applied to all files: "
            "'regex', 'llm', 'gemini', or 'hybrid'."
        ),
    ),
) -> BatchReceiptResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    parser = get_parser(strategy)
    results: list[BatchReceiptResult] = []

    for file in files:
        filename = file.filename or "unknown.pdf"
        try:
            if file.content_type not in ("application/pdf", "application/octet-stream"):
                results.append(BatchReceiptResult(
                    Filename=filename,
                    Success=False,
                    Error=f"Invalid content type: {file.content_type}. Only PDF files are accepted.",
                ))
                continue

            pdf_bytes = await file.read()
            if not pdf_bytes:
                results.append(BatchReceiptResult(
                    Filename=filename,
                    Success=False,
                    Error="Uploaded file is empty.",
                ))
                continue

            # Process based on strategy type
            if strategy in PDF_BYTES_STRATEGIES:
                receipt = parser.parse(pdf_bytes)
            elif strategy in IMAGE_STRATEGIES:
                images = pdf_to_images(pdf_bytes)
                receipt = parser.parse(images)
            else:
                images = pdf_to_images(pdf_bytes)
                raw_text = extract_text(images)
                if not raw_text.strip():
                    results.append(BatchReceiptResult(
                        Filename=filename,
                        Success=False,
                        Error="No text could be extracted from the PDF.",
                    ))
                    continue
                receipt = parser.parse(raw_text)

            results.append(BatchReceiptResult(
                Filename=filename,
                Success=True,
                Data=receipt,
            ))
            logger.info("Batch: processed %s successfully", filename)

        except Exception as e:
            logger.exception("Batch: error processing %s", filename)
            results.append(BatchReceiptResult(
                Filename=filename,
                Success=False,
                Error=str(e),
            ))

    successful = sum(1 for r in results if r.success)
    return BatchReceiptResponse(
        Total=len(results),
        Successful=successful,
        Failed=len(results) - successful,
        Results=results,
    )
