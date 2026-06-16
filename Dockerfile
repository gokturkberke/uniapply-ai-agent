# syntax=docker/dockerfile:1
FROM python:3.12-slim

# onnxruntime (pulled by fastembed) needs OpenMP at runtime; curl is used by the healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 curl \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FASTEMBED_CACHE_PATH=/cache/fastembed

WORKDIR /app

# Install dependencies first so the layer is cached across code changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# App code + the committed source manifest. The gitignored data subdirs
# (raw/normalized/chunks/index/eval) are provided at runtime via the bind-mount.
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY data/registry/ ./data/registry/

# Run as a non-root user; pre-create the cache dir so the named volume inherits its ownership.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /cache/fastembed \
    && chown -R appuser:appuser /app /cache
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -fsS http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
