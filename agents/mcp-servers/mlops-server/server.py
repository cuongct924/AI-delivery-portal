"""MCP Server providing tools for the Agent to query MLflow (experiment
tracking + model registry)."""

from mcp.server.mcpserver import MCPServer

from adapters.mlflow_adapter import MlflowAdapter

mcp = MCPServer("mlops-server")
adapter = MlflowAdapter()


@mcp.tool()
def list_experiments() -> list[dict]:
    """List models registered in the MLflow Registry."""
    return adapter.list_models()


@mcp.tool()
def get_model_metrics(name: str, version: str) -> dict:
    """Get metrics (accuracy, f1, ...) for a specific model version."""
    return adapter.get_model_metrics(name, version)


if __name__ == "__main__":
    mcp.run(transport="stdio")
