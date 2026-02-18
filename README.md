# Receipt OCR API

API-based OCR system for extracting structured information from scanned PDF receipts, built with **FastAPI** and powered by **Groq Cloud** (qwen3-32b / gpt-oss-120b).

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Parsing Strategies](#parsing-strategies)
- [Setup](#setup)
  - [Prerequisites](#prerequisites)
  - [Environment Variables](#environment-variables)
  - [Local Development](#local-development)
  - [Docker](#docker)
- [Usage](#usage)
  - [API Endpoint](#api-endpoint)
  - [cURL Examples](#curl-examples)
  - [Swagger UI](#swagger-ui)
- [Evaluation Pipeline](#evaluation-pipeline)
  - [Ground Truth Format](#ground-truth-format)
  - [Running the Evaluation](#running-the-evaluation)
  - [Metrics](#metrics)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Licenses](#licenses)

---

## Overview

This system provides REST endpoints (`POST /process_pdf` and `POST /process_batch`) that accept PDF receipts and return structured JSON containing:

- **Service Provider**: Name, Address, VAT Number
- **Transaction Details**: Items list (name, quantity, price), Currency, Total Amount, VAT

Three parsing strategies are available, allowing comparison between different pipelines.
LLM inference runs via **Groq Cloud** (ultra-fast LPU) with model selection at request time.

---

## Architecture

```
PDF Upload
    │
    ├── [hybrid]  ──► pdfplumber (native text) + OCR (image OCR) ──► Groq LLM ──► JSON
    │
    ├── [llm]     ──► PyMuPDF (PDF → images) ──► OCR ──► Groq LLM ──► JSON
    │
    └── [regex]   ──► PyMuPDF (PDF → images) ──► OCR ──► Regex heuristics ──► JSON

OCR backends: EasyOCR | PaddleOCR | Unstructured (Tesseract)
LLM models:   qwen/qwen3-32b | openai/gpt-oss-120b (via Groq Cloud)
```

---

## Parsing Strategies

| Strategy | Pipeline | Best For | Requires LLM |
|----------|----------|----------|:------------:|
| **`hybrid`** (default) | pdfplumber + OCR → merged text → Groq LLM | Mixed PDFs (native + scanned), best accuracy | ✅ |
| **`llm`** | OCR → text → Groq LLM | Scanned-only PDFs, OCR + LLM pipeline | ✅ |
| **`regex`** | OCR → text → regex | Fast, no LLM needed, limited accuracy | ❌ |

---

## Setup

### Prerequisites

- **Python 3.12+**
- **Groq Cloud API key** — sign up at [console.groq.com](https://console.groq.com) to get a free API key
- **Docker** (optional, for containerized deployment)

### Environment Variables

Create a `.env` file at the project root:

```env
# Groq Cloud API
GROQ_API_KEY=gsk_your_api_key_here

# OCR backend: easyocr (default), paddleocr, or unstructured
OCR_BACKEND=easyocr

# Langfuse tracing (optional)
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com

# Protobuf config
PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
```

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `GROQ_API_KEY` | ✅ | — | Groq Cloud API key |
| `OCR_BACKEND` | ❌ | `easyocr` | OCR engine: `easyocr`, `paddleocr`, `unstructured` |
| `LANGFUSE_SECRET_KEY` | ❌ | — | Langfuse secret key (LLM tracing) |
| `LANGFUSE_PUBLIC_KEY` | ❌ | — | Langfuse public key |
| `LANGFUSE_BASE_URL` | ❌ | `https://cloud.langfuse.com` | Langfuse server URL |

### Local Development

```bash
# 1. Clone the repository
git clone <repo-url>
cd pdf_ocr

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate it
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure your Groq API key in .env
# See https://console.groq.com for a free key

# 6. Start the server
uvicorn app.main:app --reload --port 8000
```

The API is now available at **http://localhost:8000**.

### Docker

```bash
# Docker Compose (recommended)
docker compose up --build
```

This starts the **Receipt OCR API** container on port `8000`.
LLM inference is handled remotely by Groq Cloud — no local GPU required.

---

## Usage

### API Endpoint

```
POST /process_pdf
```

| Parameter | Type | In | Default | Description |
|-----------|------|-----|---------|-------------|
| `file` | `UploadFile` | body (multipart) | *required* | PDF file to process |
| `strategy` | `string` | query | `hybrid` | Parsing strategy: `regex`, `llm`, or `hybrid` |
| `ocr_backend` | `string` | query | `easyocr` | OCR engine: `easyocr`, `paddleocr`, or `unstructured` |
| `model` | `string` | query | `qwen/qwen3-32b` | LLM model for `llm`/`hybrid` strategies |

#### Response Schema

```json
{
  "ServiceProvider": {
    "Name": "Shop XYZ",
    "Address": "123 Main Street, City, ZIP",
    "VATNumber": "VAT123456"
  },
  "TransactionDetails": {
    "Items": [
      {"Item": "Product 1", "Quantity": 2, "Price": 9.99},
      {"Item": "Product 2", "Quantity": 1, "Price": 19.99}
    ],
    "Currency": "EUR",
    "TotalAmount": 39.97,
    "VAT": "19%"
  }
}
```

### cURL Examples

```bash
# Default strategy (hybrid — pdfplumber + EasyOCR + Groq LLM)
curl -X POST "http://localhost:8000/process_pdf" \
  -F "file=@receipt.pdf"

# LLM strategy (EasyOCR + Groq LLM)
curl -X POST "http://localhost:8000/process_pdf?strategy=llm" \
  -F "file=@receipt.pdf"

# Regex strategy (no LLM required)
curl -X POST "http://localhost:8000/process_pdf?strategy=regex" \
  -F "file=@receipt.pdf"

# Use Unstructured (Tesseract) OCR backend for multilingual scanned PDFs
curl -X POST "http://localhost:8000/process_pdf?ocr_backend=unstructured&strategy=hybrid" \
  -F "file=@receipt.pdf"

# Use PaddleOCR backend
curl -X POST "http://localhost:8000/process_pdf?ocr_backend=paddleocr&strategy=llm" \
  -F "file=@receipt.pdf"

# Batch processing (multiple files)
curl -X POST "http://localhost:8000/process_batch?strategy=hybrid" \
  -F "files=@receipt1.pdf" \
  -F "files=@receipt2.pdf"
```

### Swagger UI

Interactive API documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## Evaluation Pipeline

The evaluation pipeline compares parsing strategies against manually labeled ground truth data using the [Kaggle Receipts Dataset](https://www.kaggle.com/datasets/jenswalter/receipts/data).

### Ground Truth Format

Ground truth files are stored in `evaluation/ground_truth/` as JSON:

```json
{
  "pdf_path": "data/archive/2017/de/public transport/118NP8.pdf",
  "ground_truth": {
    "ServiceProvider": {
      "Name": "DB Fernverkehr AG",
      "Address": "Stephensonstr. 1, 60326 Frankfurt",
      "VATNumber": null
    },
    "TransactionDetails": {
      "Items": [
        {"Item": "IC/EC Fahrkarte", "Quantity": 1, "Price": 78.00}
      ],
      "Currency": "EUR",
      "TotalAmount": 78.75,
      "VAT": "19%"
    }
  }
}
```

10 labeled receipts are provided covering multiple countries (DE, CA, US, FR, UK, AT).

### Running the Evaluation

```bash
# Evaluate all strategies
python -m evaluation.evaluate --strategy all

# Evaluate a specific strategy
python -m evaluation.evaluate --strategy hybrid
python -m evaluation.evaluate --strategy llm
python -m evaluation.evaluate --strategy regex

# Choose OCR backend
python -m evaluation.evaluate --strategy hybrid --ocr-backend unstructured
python -m evaluation.evaluate --strategy hybrid --ocr-backend paddleocr

# Choose LLM model
python -m evaluation.evaluate --strategy hybrid --model openai/gpt-oss-120b

# Custom ground truth directory
python -m evaluation.evaluate --strategy all --gt-dir path/to/ground_truth
```

### Metrics

The evaluation computes the following metrics per receipt, then averages across the dataset:

| Metric | Method | Description |
|--------|--------|-------------|
| **Provider Name** | Token similarity | Overlap of word tokens between prediction and ground truth |
| **Provider Address** | Token similarity | Overlap of word tokens |
| **VAT Number** | Token similarity | Overlap of word tokens |
| **Currency** | Exact match | 1.0 if match, 0.0 otherwise |
| **Total Amount** | Numeric match | Tolerance-based (±0.01) with proportional similarity |
| **VAT Info** | Token similarity | Overlap of word tokens |
| **Items F1** | Precision / Recall / F1 | Item-level matching based on name, quantity, and price |

Output example:

```
=======================================================
  Strategy: HYBRID (10 receipts)
=======================================================
  Field                      Avg Similarity
  ----------------------------------------
  Provider Name                       92.5%
  Provider Address                    85.0%
  VAT Number                          78.3%
  Currency                            90.0%
  Total Amount                        95.0%
  VAT Info                            80.0%
  Items F1                            72.5%
  ----------------------------------------
  Avg Latency                          2.3s
```

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run a specific test file
pytest tests/test_router.py -v
pytest tests/test_llm_parser.py -v
pytest tests/test_receipt_parser.py -v
```

---

## Project Structure

```
pdf_ocr/
├── .env                          # Environment variables (GROQ_API_KEY, LANGFUSE_*, OCR_BACKEND)
├── Dockerfile                    # Multi-stage container definition
├── docker-compose.yaml           # Docker Compose (API service)
├── requirements.txt              # Python dependencies
├── app/
│   ├── main.py                   # FastAPI application entry point
│   ├── routers/
│   │   └── receipt.py            # POST /process_pdf + /process_batch endpoints
│   ├── schemas/
│   │   └── receipt.py            # Pydantic response models
│   └── services/
│       ├── parser_factory.py     # Strategy enum & parser instantiation
│       ├── base_ocr.py           # Abstract base class for OCR backends
│       ├── base_llm.py           # Abstract base class for LLM backends
│       ├── ocr_engine.py         # OCR facade — delegates to selected backend
│       ├── easyocr_tool.py       # EasyOCR backend (18+ languages)
│       ├── paddleocr_tool.py     # PaddleOCR backend
│       ├── unstructured_tool.py  # Unstructured + Tesseract backend (multilingual OCR)
│       ├── groq_client.py        # Groq Cloud LLM client (with Langfuse tracing)
│       ├── ollama_client.py      # Legacy shim → delegates to Groq
│       ├── llm_parser.py         # OCR text → LLM → JSON
│       ├── hybrid_parser.py      # pdfplumber + OCR → LLM → JSON
│       ├── receipt_parser.py     # Regex-based parser (no LLM)
│       ├── pdf_converter.py      # PDF → PIL Images (PyMuPDF)
│       ├── pdfplumber_extractor.py # PDF → text (pdfplumber)
│       └── json_utils.py         # JSON parsing, prompts & post-processing
├── evaluation/
│   ├── evaluate.py               # Evaluation pipeline CLI
│   ├── metrics.py                # Scoring functions (similarity, F1, etc.)
│   └── ground_truth/             # 10 labeled receipt JSON files
├── data/
│   └── archive/                  # Kaggle Receipts Dataset (by year/country)
└── tests/                        # Unit tests (pytest)
```

---

## Licenses

1. Instructions and code provided by the company belong exclusively to them.
2. Code written by the candidate belongs to them. Rights are granted for use, analysis, storage, and review as part of the recruitment process.
