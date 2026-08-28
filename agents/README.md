# agents

Central module for AI Agent & MCP (Model Context Protocol).

- `mcp-servers/` — each MCP server is an independent process (packaged as its
  own Docker image), exposing tools over the MCP protocol for Claude (running
  inside `services/orchestration-api`) to call. Contains no complex business
  logic — calls through `adapters/`.
  - `mlops-server/` — MLflow tools (`list_experiments`, `get_model_metrics`)
  - `k8s-server/` — read-only K8s tools (mock, not wired to a real cluster yet)
  - `metrics-server/` — Prometheus query tools (drift/latency)
- `skills/` — specific business logic (e.g. evaluating model drift), calls
  `adapters/` directly; reusable from both MCP tools and regular FastAPI routes.

Prompt/persona content lives in one place, not here —
`services/orchestration-api/routers/prompts.py` (backed by
`adapters/version_registry_adapter.py`), read by `plugins/prompt-registry/`
(Backstage UI) and `routers/chat.py`. A duplicate static copy used to live
at `agents/prompts/`; removed once nothing imported it.

## Try running an MCP server locally

```bash
bash scripts/run-mcp-local.sh mlops   # or: k8s | metrics
```
