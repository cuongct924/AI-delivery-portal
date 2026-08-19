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
- `prompts/` — Prompt Registry (Python version): system prompt / persona for
  each type of Agent. The UI-managed version lives in `plugins/prompt-registry/`
  (Backstage) + `services/orchestration-api/routers/prompts.py` (API).

## Try running an MCP server locally

```bash
bash scripts/run-mcp-local.sh mlops   # or: k8s | metrics
```
