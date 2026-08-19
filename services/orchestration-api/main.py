"""FastAPI BFF — acts as an MCP Client, routing requests from the Portal UI
to the AI LLM (Claude)."""

from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator
from routers import chat, prompts

app = FastAPI(title="AI Delivery Portal — Orchestration API")
app.include_router(chat.router)
app.include_router(prompts.router)

# Expose /metrics — scraped by Prometheus (infra/monitoring/prometheus.yml)
Instrumentator().instrument(app).expose(app)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}
