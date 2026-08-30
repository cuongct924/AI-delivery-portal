# agents

Central module for AI Agent & MCP (Model Context Protocol).

- `mcp-servers/` — each MCP server is an independent process (packaged as its
  own Docker image), exposing tools over the MCP protocol for Claude (running
  inside `services/orchestration-api`) to call. Split by functional domain,
  not by backend: read-only "health" tools vs. action tools. Both use
  `streamable-http` transport (not `stdio`) so `orchestration-api` can
  discover and connect to them at runtime via the Backstage Catalog
  (`services/orchestration-api/catalog_client.py`) instead of a hardcoded
  local path.
  - `mlops-observability-server/` — read-only: MLflow (`list_experiments`,
    `get_model_metrics`), K8s (mock, not wired to a real cluster yet),
    Prometheus (`query_metric`, `check_model_latency`).
  - `golden-paths-server/` — the 6 LLMOps Lifecycle Golden Path actions
    (draft/evaluate/activate prompt, rag ingest/evaluate/activate), each a
    thin HTTP client into `services/orchestration-api`'s existing endpoints.
    Contains no complex business logic — calls through `adapters/`.
- `skills/` — specific business logic (e.g. evaluating model drift), calls
  `adapters/` directly; reusable from both MCP tools and regular FastAPI routes.

Prompt/persona content lives in one place, not here —
`services/orchestration-api/routers/prompts.py` (backed by
`adapters/version_registry_adapter.py`), read by `plugins/prompt-registry/`
(Backstage UI) and `routers/chat.py`. A duplicate static copy used to live
at `agents/prompts/`; removed once nothing imported it.

## Try running an MCP server locally

```bash
bash scripts/run-mcp-local.sh observability   # or: golden-paths
```
