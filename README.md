# Receipt OCR API

API-based OCR system for extracting structured information from scanned PDF receipts, built with **FastAPI** and powered by **Ollama (qwen2.5)**.

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

Four parsing strategies are available, allowing comparison between different pipelines.
All LLM inference runs **locally** via Ollama (qwen2.5) — no cloud API needed.

---

## Architecture

```
PDF Upload
    │
    ├── [gemini]  ──► PyMuPDF (PDF → images) ──► EasyOCR ──► Ollama (qwen2.5) ──► JSON
    │
    ├── [llm]     ──► PyMuPDF (PDF → images) ──► EasyOCR ──► Ollama (qwen2.5) ──► JSON
    │
    ├── [hybrid]  ──► pdfplumber (native text) + EasyOCR (image OCR) ──► Ollama (qwen2.5) ──► JSON
    │
    └── [regex]   ──► PyMuPZ (PDF → images) ──► EasyOCR ──► Regex heuristics ──► JSON
```

---

## Parsing Strategies

| Strategy | Pipeline | Best For | Requires LLM |
|----------|----------|----------|:------------:|
| **`hybrid`** (default) | pdfplumber + EasyOCR → merged text → Ollama | Mixed PDFs (native + scanned), best accuracy | ✅ |
| **`gemini`** | EasyOCR → text → Ollama | Scanned receipts (legacy name) | ✅ |
| **`llm`** | EasyOCR → text → Ollama | Comparing OCR+LLM pipelines | ✅ |
| **`regex`** | EasyOCR → text → regex | Fast, no LLM needed, limited accuracy | ❌ |

---

## Setup

### Prerequisites

- **Python 3.12+**
- **Ollama** — install from [ollama.com](https://ollama.com) and pull the model: `ollama pull qwen2.5:latest`
- **Docker** (optional, for containerized deployment — Ollama included in docker-compose)

### Environment Variables

Create a `.env` file at the project root:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:latest
```

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `OLLAMA_BASE_URL` | ❌ | `http://localhost:11434` | Ollama server URL |
| `OLLAMA_MODEL` | ❌ | `qwen2.5:latest` | Ollama model tag |

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

# 5. Install and start Ollama, pull the model
# See https://ollama.com for installation
ollama pull qwen2.5:latest

# 6. Start the server
uvicorn app.main:app --reload --port 8000
```

The API is now available at **http://localhost:8000**.

### Docker

```bash
# Docker Compose (recommended — includes Ollama + model pull + API)
docker compose up --build
```

This starts 3 services:
1. **ollama** — LLM server on port `11434`
2. **ollama-pull** — one-shot init container that pulls `qwen2.5:latest`
3. **api** — FastAPI on port `8000` (waits for model to be ready)

---

## Usage

### API Endpoint

```
POST /process_pdf
```

| Parameter | Type | In | Default | Description |
|-----------|------|-----|---------|-------------|
| `file` | `UploadFile` | body (multipart) | *required* | PDF file to process |
| `strategy` | `string` | query | `hybrid` | Parsing strategy: `regex`, `llm`, `gemini`, or `hybrid` |

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
# Default strategy (hybrid — pdfplumber + EasyOCR + Ollama)
curl -X POST "http://localhost:8000/process_pdf" \
  -F "file=@receipt.pdf"

# Gemini strategy (EasyOCR + Ollama)
curl -X POST "http://localhost:8000/process_pdf?strategy=gemini" \
  -F "file=@receipt.pdf"

# LLM strategy (EasyOCR + Ollama)
curl -X POST "http://localhost:8000/process_pdf?strategy=llm" \
  -F "file=@receipt.pdf"

# Regex strategy (no LLM required)
curl -X POST "http://localhost:8000/process_pdf?strategy=regex" \
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
python -m evaluation.evaluate --strategy gemini
python -m evaluation.evaluate --strategy llm
python -m evaluation.evaluate --strategy regex

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
pytest tests/test_gemini_parser.py -v
pytest tests/test_llm_parser.py -v
pytest tests/test_receipt_parser.py -v
```

---

## Project Structure

```
pdf_ocr/
├── .env                          # Environment variables (OLLAMA_BASE_URL, OLLAMA_MODEL)
├── Dockerfile                    # Multi-stage container definition
├── docker-compose.yaml           # Docker Compose (API + Ollama + model pull)
├── requirements.txt              # Python dependencies
├── app/
│   ├── main.py                   # FastAPI application entry point
│   ├── routers/
│   │   └── receipt.py            # POST /process_pdf + /process_batch endpoints
│   ├── schemas/
│   │   └── receipt.py            # Pydantic response models
│   └── services/
│       ├── parser_factory.py     # Strategy enum & parser instantiation
│       ├── ollama_client.py      # Shared Ollama client (chat_completion)
│       ├── gemini_parser.py      # EasyOCR → Ollama → JSON
│       ├── llm_parser.py         # OCR text → Ollama → JSON
│       ├── hybrid_parser.py      # pdfplumber + EasyOCR → Ollama → JSON
│       ├── receipt_parser.py     # Regex-based parser (no LLM)
│       ├── ocr_engine.py         # EasyOCR wrapper with language support
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
