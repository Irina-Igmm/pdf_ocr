# Receipt OCR API

API-based OCR system for extracting structured information from scanned PDF receipts, built with **FastAPI** and powered by **Google Gemini 2.0 Flash**.

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

This system provides a single REST endpoint (`POST /process_pdf`) that accepts a PDF receipt and returns structured JSON containing:

- **Service Provider**: Name, Address, VAT Number
- **Transaction Details**: Items list (name, quantity, price), Currency, Total Amount, VAT

Five parsing strategies are available, allowing comparison between different pipelines.

---

## Architecture

```
PDF Upload
    │
    ├── [gemini]  ──► PyMuPDF (PDF → images) ──► Gemini 2.0 Flash (multimodal) ──► JSON
    │
    ├── [llm]     ──► PyMuPDF (PDF → images) ──► EasyOCR ──► Gemini 2.0 Flash (text) ──► JSON
    │
    ├── [hybrid]  ──► pdfplumber (native text) + EasyOCR (image OCR) ──► Gemini 2.0 Flash ──► JSON
    │
    ├── [native]  ──► pdfplumber (native text) ──► Gemini 2.0 Flash (text) ──► JSON
    │
    └── [regex]   ──► PyMuPDF (PDF → images) ──► EasyOCR ──► Regex heuristics ──► JSON
```

---

## Parsing Strategies

| Strategy | Pipeline | Best For | Requires API |
|----------|----------|----------|:------------:|
| **`gemini`** (default) | Image → Gemini 2.0 Flash | Scanned receipts, best accuracy | ✅ |
| **`llm`** | EasyOCR → text → Gemini | Comparing OCR+LLM vs vision | ✅ |
| **`hybrid`** | pdfplumber + EasyOCR → merged text → Gemini | Mixed PDFs (some native, some scanned) | ✅ |
| **`native`** | pdfplumber → text → Gemini | Digital/native PDFs with embedded text | ✅ |
| **`regex`** | EasyOCR → text → regex | Fast, no API key needed, limited accuracy | ❌ |

---

## Setup

### Prerequisites

- **Python 3.12+**
- **Google Gemini API key** — get one at [Google AI Studio](https://aistudio.google.com/apikey)
- **Docker** (optional, for containerized deployment)

### Environment Variables

Create a `.env` file at the project root:

```env
GEMINI_API_KEY=your_gemini_api_key_here
MODEL_ID=gemini-2.0-flash
```

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `GEMINI_API_KEY` | ✅ | — | Google Gemini API key |
| `MODEL_ID` | ❌ | `gemini-2.0-flash` | Gemini model identifier |

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

# 5. Create .env file with your API key
echo GEMINI_API_KEY=your_key_here > .env
echo MODEL_ID=gemini-2.0-flash >> .env

# 6. Start the server
uvicorn app.main:app --reload --port 8000
```

The API is now available at **http://localhost:8000**.

### Docker

```bash
# Option 1: Docker Compose (recommended)
docker compose up --build

# Option 2: Docker standalone
docker build -t receipt-ocr .
docker run -p 8000:8000 -e GEMINI_API_KEY=your_key_here receipt-ocr
```

---

## Usage

### API Endpoint

```
POST /process_pdf
```

| Parameter | Type | In | Default | Description |
|-----------|------|-----|---------|-------------|
| `file` | `UploadFile` | body (multipart) | *required* | PDF file to process |
| `strategy` | `string` | query | `gemini` | Parsing strategy: `regex`, `llm`, `gemini`, `hybrid`, `native` |

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
# Default strategy (gemini — multimodal image → JSON)
curl -X POST "http://localhost:8000/process_pdf" \
  -F "file=@receipt.pdf"

# Hybrid strategy (pdfplumber + EasyOCR + Gemini)
curl -X POST "http://localhost:8000/process_pdf?strategy=hybrid" \
  -F "file=@receipt.pdf"

# Native PDF strategy (pdfplumber + Gemini, for digital PDFs)
curl -X POST "http://localhost:8000/process_pdf?strategy=native" \
  -F "file=@receipt.pdf"

# LLM strategy (EasyOCR + Gemini text)
curl -X POST "http://localhost:8000/process_pdf?strategy=llm" \
  -F "file=@receipt.pdf"

# Regex strategy (no API key required)
curl -X POST "http://localhost:8000/process_pdf?strategy=regex" \
  -F "file=@receipt.pdf"
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
python -m evaluation.evaluate --strategy gemini
python -m evaluation.evaluate --strategy hybrid
python -m evaluation.evaluate --strategy native
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
  Strategy: GEMINI (10 receipts)
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
├── .env                          # Environment variables (GEMINI_API_KEY, MODEL_ID)
├── Dockerfile                    # Container definition
├── docker-compose.yaml           # Docker Compose configuration
├── requirements.txt              # Python dependencies
├── app/
│   ├── main.py                   # FastAPI application entry point
│   ├── routers/
│   │   └── receipt.py            # POST /process_pdf endpoint
│   ├── schemas/
│   │   └── receipt.py            # Pydantic response models
│   └── services/
│       ├── parser_factory.py     # Strategy enum & parser instantiation
│       ├── gemini_parser.py      # Image → Gemini multimodal → JSON
│       ├── llm_parser.py         # OCR text → Gemini text → JSON
│       ├── hybrid_parser.py      # pdfplumber + EasyOCR → Gemini → JSON
│       ├── native_parser.py      # pdfplumber → Gemini → JSON
│       ├── receipt_parser.py     # Regex-based parser (no API)
│       ├── ocr_engine.py         # EasyOCR wrapper with language support
│       ├── pdf_converter.py      # PDF → PIL Images (PyMuPDF)
│       ├── pdfplumber_extractor.py # PDF → text (pdfplumber)
│       └── json_utils.py         # LLM JSON parsing & schema prompt
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
