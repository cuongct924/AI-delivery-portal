# checkov:skip=CKV_DOCKER_2: batch job (Argo Workflow pod runs train.py once
# and exits) — no long-running process to health-check, unlike a service.
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir uv
COPY infra/argo-workflows/training-image/requirements.lock.txt .
# Installed at build time, not by train-step at pod startup — a Docker
# Desktop I/O error hit mid-download when this used to run on every job.
RUN uv pip install --system --no-cache -r requirements.lock.txt
COPY infra/argo-workflows/training-image/*.py .
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser
ENV PYTHONPATH=/app
CMD ["python", "train.py"]
