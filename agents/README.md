# agents

Central module for AI Agent & MCP (Model Context Protocol).

- `mcp-servers/` — each MCP server is an independent process exposing tools
  over MCP for `orchestration-api` to call. Split by functional domain:
  read-only "health" vs. action. `streamable-http` transport, discovered
  via the Backstage Catalog (`catalog_client.py`), not a hardcoded path.
  - `observability-server/` — read-only: MLflow, K8s (mock),
    Prometheus.
  - `golden-paths-server/` — the 6 LLMOps Lifecycle Golden Path actions,
    thin HTTP clients into `orchestration-api`.
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
