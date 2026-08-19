"""MCP Server that queries Prometheus — used by Claude when asked "is the model
drifting or responding slowly?". Connects to the Prometheus instance set up by
docker-compose.yml (infra/monitoring/prometheus.yml is the scrape config).
"""

import os

import httpx
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("metrics-server")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://localhost:9090")


@mcp.tool()
def query_metric(promql: str) -> dict:
    """Run a PromQL instant query, returning the raw result from Prometheus."""
    response = httpx.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": promql}, timeout=10)
    response.raise_for_status()
    return response.json()


@mcp.tool()
def check_model_latency(model_name: str, threshold_ms: float = 500) -> dict:
    """Check whether a model's p95 latency exceeds a threshold (assumes the
    `model_inference_duration_ms` metric is exposed by KServe/BentoML, labeled by model)."""
    promql = (
        "histogram_quantile(0.95, sum(rate("
        f'model_inference_duration_ms_bucket{{model="{model_name}"}}[5m])) by (le))'
    )
    result = query_metric(promql)
    values = result.get("data", {}).get("result", [])
    p95 = float(values[0]["value"][1]) if values else None
    return {
        "model": model_name,
        "p95_latency_ms": p95,
        "threshold_ms": threshold_ms,
        "breached": p95 is not None and p95 > threshold_ms,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
