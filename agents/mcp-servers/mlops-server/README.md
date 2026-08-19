# mlops-server

MCP server exposing the `list_experiments`, `get_model_metrics` tools — reads
data from MLflow (`adapters/mlflow_adapter.py`) set up via `docker compose up mlflow`.

## Run locally

```bash
bash scripts/run-mcp-local.sh mlops
```
