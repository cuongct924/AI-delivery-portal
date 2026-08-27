# Multi-stage — dependencies resolved in `builder`, only the installed
# site-packages copied into the final image; uv and pip's build cache never
# ship in the final image.
FROM python:3.12-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv
# Copied before the app code so this layer (the slow one) is cache-hit on
# every rebuild that only touches app code, not requirements.lock.txt.
COPY services/orchestration-api/requirements.lock.txt .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --target /deps -r requirements.lock.txt

FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*
COPY --from=builder /deps /usr/local/lib/python3.12/site-packages
RUN useradd --create-home --uid 1000 appuser
# routers/models.py and evaluations/llm_judge.py import from adapters/, which
# lives outside this service's own directory — needs repo-root build context.
COPY --chown=appuser:appuser adapters/ ./adapters/
COPY --chown=appuser:appuser services/orchestration-api/ .
USER appuser
EXPOSE 8000
ENV PYTHONPATH=/app
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/healthz')" || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
