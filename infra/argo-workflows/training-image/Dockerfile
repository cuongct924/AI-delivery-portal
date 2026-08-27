# Multi-stage: dependencies (~1.5GB with sklearn/xgboost/lightgbm/catboost,
# much of it build/wheel cache) are resolved in `builder` and only the
# installed site-packages are copied into the final stage — uv itself, pip's
# cache, and apt lists never end up in the image that actually ships.
FROM python:3.12-slim AS builder
WORKDIR /app
RUN pip install --no-cache-dir uv
# Copied before the app code so this layer (the slow one) is cache-hit on
# every rebuild that only touches *.py, not requirements.lock.txt.
COPY infra/argo-workflows/training-image/requirements.lock.txt .
# Installed at build time, not by train-step at pod startup — a Docker
# Desktop I/O error hit mid-download when this used to run on every job.
# --index-strategy unsafe-best-match: requirements.lock.txt embeds both
# PyPI and download.pytorch.org (torch CPU wheels) as trusted indexes
# (Makefile's `lock` target) — uv's dependency-confusion-safe default
# otherwise refuses versions of unrelated packages past what the *first*
# index offers.
RUN uv pip install --system --no-cache --index-strategy unsafe-best-match \
    --target /deps -r requirements.lock.txt

# checkov:skip=CKV_DOCKER_2: batch job (Argo Workflow pod runs train.py once
# and exits) — no long-running process to health-check, unlike a service.
FROM python:3.12-slim
WORKDIR /app
RUN apt-get update && apt-get upgrade -y \
    # libgomp1: LightGBM's Linux wheel links against it at import time,
    # doesn't bundle it. git: byoc_runner.py shells out to it to clone a
    # Dev's BYOC repo (mục 6b.3) — the only 2 runtime (non-Python)
    # dependencies here.
    && apt-get install -y --no-install-recommends libgomp1 git \
    && rm -rf /var/lib/apt/lists/*
COPY --from=builder /deps /usr/local/lib/python3.12/site-packages
COPY infra/argo-workflows/training-image/*.py .
RUN useradd --create-home --uid 1000 appuser
USER appuser
ENV PYTHONPATH=/app
CMD ["python", "train.py"]
