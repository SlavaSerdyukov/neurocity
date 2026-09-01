FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NEUROCITY_APP_NAME=NEUROCITY \
    NEUROCITY_DATABASE_URL=sqlite:////data/neurocity.db \
    NEUROCITY_DEFAULT_SEED=2049 \
    NEUROCITY_DEFAULT_POPULATION=5000 \
    NEUROCITY_DEFAULT_DISTRICTS=14 \
    NEUROCITY_ENABLE_LLM=false \
    NEUROCITY_OLLAMA_URL=http://localhost:11434 \
    NEUROCITY_OLLAMA_MODEL=qwen2.5

WORKDIR /app

COPY pyproject.toml README.md ./
COPY app ./app

RUN pip install --upgrade pip && pip install . && mkdir -p /data

EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
