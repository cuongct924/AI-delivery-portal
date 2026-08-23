"""FastAPI BFF — acts as an MCP Client, routing requests from the Portal UI
to the AI LLM (Claude)."""

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from routers import chat, prompts

app = FastAPI(title="AI Delivery Portal — Orchestration API")
app.include_router(chat.router)
app.include_router(prompts.router)
# TODO: add routers/models.py — /register-model, /trigger-training endpoints
# for the `orchestration:register-model`/`orchestration:trigger-training` actions.
# TODO: add policies/ (Chain of Responsibility) + /policy-check endpoint for
# the `orchestration:policy-check` Custom Scaffolder Action (Golden Path #2).

# Expose /metrics — scraped by Prometheus (infra/monitoring/prometheus.yml)
Instrumentator().instrument(app).expose(app)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}
