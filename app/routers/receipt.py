import logging
import os

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.schemas.receipt import BatchReceiptResponse, BatchReceiptResult, ReceiptResponse
from app.services.ocr_engine import extract_text
from app.services.parser_factory import (
    LLMModel,
    OCRBackend,
    PDF_BYTES_STRATEGIES,
    ParsingStrategy,
    get_llm_client,
    get_parser,
)
from app.services.pdf_converter import pdf_to_images

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Receipt OCR"])

# Default OCR backend from env (fallback: easyocr)
_DEFAULT_OCR = OCRBackend(os.getenv("OCR_BACKEND", "easyocr"))


def _set_ocr_backend(backend: OCRBackend) -> None:
    """Switch the OCR backend at runtime by updating the facade singleton."""
    os.environ["OCR_BACKEND"] = backend.value
    # Reload the backend in the facade module
    from app.services import ocr_engine
    ocr_engine._backend = ocr_engine._load_backend()


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
        description="Parsing strategy: 'regex', 'llm', or 'hybrid'.",
    ),
    ocr_backend: OCRBackend = Query(
        default=_DEFAULT_OCR,
        description="OCR engine: 'easyocr', 'paddleocr', or 'unstructured'.",
    ),
    model: LLMModel = Query(
        default=LLMModel.GROQ_QWEN3,
        description="LLM model for llm/hybrid strategies.",
    ),
) -> ReceiptResponse:
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Set the OCR backend for this request
    _set_ocr_backend(ocr_backend)

    # Build the LLM client and parser
    llm_client = get_llm_client(model)
    parser = get_parser(strategy, llm_client=llm_client)

    # Strategies that handle PDF bytes internally (pdfplumber-based)
    if strategy in PDF_BYTES_STRATEGIES:
        return parser.parse(pdf_bytes)

    images = pdf_to_images(pdf_bytes)

    # Text-based strategies (regex, llm) — need OCR first
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
        description="Parsing strategy applied to all files: 'regex', 'llm', or 'hybrid'.",
    ),
    ocr_backend: OCRBackend = Query(
        default=_DEFAULT_OCR,
        description="OCR engine: 'easyocr', 'paddleocr', or 'unstructured'.",
    ),
    model: LLMModel = Query(
        default=LLMModel.GROQ_QWEN3,
        description="LLM model for llm/hybrid strategies.",
    ),
) -> BatchReceiptResponse:
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    # Set the OCR backend for this batch
    _set_ocr_backend(ocr_backend)

    llm_client = get_llm_client(model)
    parser = get_parser(strategy, llm_client=llm_client)
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
