# mlops-observability-server

MCP server for the "system/model health" domain — read-only, merges what
used to be 3 separate servers (`mlops-server`, `k8s-server`, `metrics-server`).

Tools:
- `list_experiments`, `get_model_metrics` — reads MLflow
  (`adapters/mlflow_adapter.py`), set up via `docker compose up mlflow`.
- `check_pod_status`, `get_logs` — currently **mock** (not wired to a real
  K8s cluster). Integrate the `kubernetes` Python client when a real cluster
  is available, and add RBAC/OPA policy in `infra/opa-policies/` before
  granting write access.
- `query_metric` (free-form PromQL), `check_model_latency` — reads
  Prometheus (set up via `docker compose up`, scrape config at
  `infra/monitoring/prometheus.yml`).

Transport: `streamable-http` — discovered via the Backstage Catalog, not a
local subprocess. `MCP_HOST`/`MCP_PORT` (default `0.0.0.0:9001`).

## Run locally

```bash
bash scripts/run-mcp-local.sh observability
```
