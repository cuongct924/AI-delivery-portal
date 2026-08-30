"""FastAPI BFF — acts as an MCP Client, routing requests from the Portal UI
to the AI LLM (Claude, or any model registered in
infra/llm-gateways/litellm-config.yaml)."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from mcp_client import McpToolRegistry
from prometheus_fastapi_instrumentator import Instrumentator
from routers import chat, llm_serving, models, monitoring, prompts, rag, recommendations

# Without this, the root logger defaults to WARNING and every app-level
# logger.info() call (e.g. auth/keycloak.py's authenticated-identity line)
# is silently dropped — uvicorn only configures its own uvicorn.* loggers.
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    registry = McpToolRegistry()
    # connect_all() never raises — a Catalog/MCP server outage must not
    # prevent orchestration-api from starting; chat just serves
    # use_tools=False requests until connectivity is restored.
    await registry.connect_all()
    app.state.mcp_registry = registry
    yield
    await registry.aclose()


app = FastAPI(title="AI Delivery Portal — Orchestration API", lifespan=lifespan)
app.include_router(chat.router)
app.include_router(prompts.router)
app.include_router(models.router)
app.include_router(recommendations.router)
app.include_router(monitoring.router)
app.include_router(llm_serving.router)
app.include_router(rag.router)

# Expose /metrics — scraped by Prometheus (infra/monitoring/prometheus.yml)
Instrumentator().instrument(app).expose(app)


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}
