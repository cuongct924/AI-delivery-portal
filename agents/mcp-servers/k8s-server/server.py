"""MCP Server that reads Kubernetes status (read-only, no write/delete permission).

Currently returns mock data — swap in the real kubernetes-client when
integrating a real cluster.
"""

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("k8s-server")


@mcp.tool()
def check_pod_status(namespace: str, pod_name: str) -> dict:
    """Check the status of a pod. (mock — not wired to a real cluster yet)"""
    return {
        "namespace": namespace,
        "pod_name": pod_name,
        "status": "Running",
        "note": "mock data — not wired to a real cluster yet",
    }


@mcp.tool()
def get_logs(namespace: str, pod_name: str, tail_lines: int = 50) -> str:
    """Get the most recent logs for a pod. (mock — not wired to a real cluster yet)"""
    return f"[mock log] last {tail_lines} lines of {pod_name} in {namespace}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
