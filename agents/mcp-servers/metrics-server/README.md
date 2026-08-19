# metrics-server

MCP server exposing the `query_metric` (free-form PromQL) and
`check_model_latency` tools — reads data from Prometheus (set up via
`docker compose up`, scrape config at `infra/monitoring/prometheus.yml`).

## Run locally

```bash
bash scripts/run-mcp-local.sh metrics
```
