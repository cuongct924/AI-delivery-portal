"""MCP Server for the "system/model health" domain — read-only, merges
what used to be 3 separate servers (mlops/k8s/metrics). See
agents/mcp-servers/golden-paths-server/ for the write-side domain.
"""

import os
from typing import Final, TypedDict

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from adapters.interfaces import ModelSummary
from adapters.mlflow_adapter import MlflowAdapter

mcp = MCPServer("mlops-observability-server")
adapter = MlflowAdapter()
PROMETHEUS_URL: Final[str] = os.getenv("PROMETHEUS_URL", "http://localhost:9090")

READ_ONLY: Final = ToolAnnotations(read_only_hint=True)


class PodStatus(TypedDict):
    namespace: str
    pod_name: str
    status: str
    note: str


class LatencyCheck(TypedDict):
    model: str
    namespace: str
    p95_latency_ms: float | None
    threshold_ms: float
    breached: bool


class PromotionStatus(TypedDict):
    model: str
    tenant: str
    environments: dict[str, str]
    prod_pending_approval: bool
    note: str


@mcp.tool(annotations=READ_ONLY)
def list_experiments() -> list[ModelSummary]:
    """List models registered in the MLflow Registry."""
    return adapter.list_models()


@mcp.tool(annotations=READ_ONLY)
def get_model_metrics(name: str, version: str) -> dict[str, float]:
    """Get metrics (accuracy, f1, ...) for a specific model version."""
    return adapter.get_model_metrics(name, version)


@mcp.tool(annotations=READ_ONLY)
def check_pod_status(namespace: str, pod_name: str) -> PodStatus:
    """Check the status of a pod. (mock — not wired to a real cluster yet)"""
    return {
        "namespace": namespace,
        "pod_name": pod_name,
        "status": "Running",
        "note": "mock data — not wired to a real cluster yet",
    }


@mcp.tool(annotations=READ_ONLY)
def get_logs(namespace: str, pod_name: str, tail_lines: int = 50) -> str:
    """Get the most recent logs for a pod. (mock — not wired to a real cluster yet)"""
    return f"[mock log] last {tail_lines} lines of {pod_name} in {namespace}"


@mcp.tool(annotations=READ_ONLY)
def query_metric(promql: str) -> dict[str, object]:
    """Run a PromQL instant query, returning the raw result from Prometheus."""
    response = httpx.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": promql}, timeout=10)
    response.raise_for_status()
    return response.json()


@mcp.tool(annotations=READ_ONLY)
def check_model_latency(model_name: str, namespace: str, threshold_ms: float = 500) -> LatencyCheck:
    """Check whether a model's p95 latency exceeds a threshold (assumes the
    `model_inference_duration_ms` metric is exposed by KServe/BentoML, labeled by model
    and namespace). `namespace` is required, not optional — with
    infra/environments/{dev,staging,prod}/inference-services/{mlops-team,llmops-team}/,
    the same model_name can be deployed in multiple namespaces
    (ai-delivery-portal-<env>-<tenant>) at once, so a query with no namespace
    filter would silently aggregate across all of them."""
    promql = (
        "histogram_quantile(0.95, sum(rate("
        f'model_inference_duration_ms_bucket{{model="{model_name}", namespace="{namespace}"}}'
        "[5m])) by (le))"
    )
    result = query_metric(promql)
    data = result.get("data")
    values = data.get("result", []) if isinstance(data, dict) else []
    p95 = float(values[0]["value"][1]) if values else None
    return {
        "model": model_name,
        "namespace": namespace,
        "p95_latency_ms": p95,
        "threshold_ms": threshold_ms,
        "breached": p95 is not None and p95 > threshold_ms,
    }


@mcp.tool(annotations=READ_ONLY)
def get_promotion_status(model_name: str, tenant: str) -> PromotionStatus:
    """Check which environments a model has reached via Kargo's promotion
    pipeline, and whether a prod promotion is waiting on manual approval.
    (mock — not wired to a real Kargo installation yet; see infra/kargo/README.md
    for the Warehouse/Stage naming this would query:
    infra/kargo/warehouse-inference-services-<tenant>.yaml,
    infra/kargo/stage-{staging,prod}-<tenant>.yaml). Read-only by design —
    approving a prod promotion stays a human action via `kargo approve`/the
    Kargo UI, never something this tool (or any agent) can trigger."""
    return {
        "model": model_name,
        "tenant": tenant,
        "environments": {"dev": "unknown", "staging": "unknown", "prod": "unknown"},
        "prod_pending_approval": False,
        "note": "mock data — infra/kargo/ is not installed/verified in this environment yet",
    }


if __name__ == "__main__":
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "9001"))
    mcp.run(transport="streamable-http", host=host, port=port)
