# ── Stage 1: Builder ─────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

ENV PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

# Install system dependencies for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    cmake \
    libgl1 \
    libglib2.0-0 \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-fra \
    tesseract-ocr-deu \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Stage 2: Runtime ─────────────────────────────────────────────
FROM python:3.11-slim

WORKDIR /app

# Runtime system dependencies + Tesseract OCR (for unstructured backend)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    curl \
    # Tesseract OCR engine + language packs (used by unstructured backend)
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-deu \
    tesseract-ocr-fra \
    tesseract-ocr-spa \
    tesseract-ocr-nld \
    tesseract-ocr-pol \
    tesseract-ocr-ces \
    tesseract-ocr-swe \
    tesseract-ocr-ita \
    tesseract-ocr-por \
    tesseract-ocr-hrv \
    # poppler for PDF rendering (used by unstructured)
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY app/ ./app/
COPY evaluation/ ./evaluation/
# .env is injected by docker-compose, not baked into image
# COPY .env .env

# Create non-root user
RUN useradd -m appuser
USER appuser
ENV HOME=/home/appuser

# Pre-download EasyOCR models (English + common languages) to user home
RUN python -c "import easyocr; reader = easyocr.Reader(['en', 'de', 'fr', 'es', 'it'], gpu=False)" 2>/dev/null || true

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]