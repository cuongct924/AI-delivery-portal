"""MCP Server for the LLMOps Lifecycle Golden Path actions — the "action"
domain, separate from mlops-observability-server's read-only "health"
domain. Each tool is a thin HTTP client into services/orchestration-api's
existing endpoints (the same ones
packages/backend/src/actions/mlopsActions.ts calls) — no business logic
duplicated here.

Requires orchestration-api running with AUTH_ENABLED=false (dev-bypass) — no
machine-to-machine auth exists yet, a known and accepted limitation for
local/demo scope (see README.md).
"""

import os
from typing import TypedDict

import httpx
from keycloak_client import auth_headers
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

mcp = MCPServer("golden-paths-server")
ORCHESTRATION_API_URL = os.getenv("ORCHESTRATION_API_URL", "http://localhost:8000")

AUTO_EXECUTABLE = ToolAnnotations(read_only_hint=False)
# destructive_hint=True signals the caller (routers/chat.py's tool-calling
# loop) that this mutates live state and must go through a human
# confirmation step before ever being invoked — LLMOps has no PR-gate
# equivalent to fall back on.
NEEDS_CONFIRMATION = ToolAnnotations(read_only_hint=False, destructive_hint=True)


class EvalCase(TypedDict):
    question: str


def _post(path: str, payload: dict) -> dict:
    response = httpx.post(
        f"{ORCHESTRATION_API_URL}{path}", json=payload, headers=auth_headers(), timeout=30
    )
    response.raise_for_status()
    return response.json()


@mcp.tool(annotations=AUTO_EXECUTABLE)
def draft_prompt(name: str, persona: str, content: str) -> dict:
    """Register a new (inactive) prompt version."""
    return _post("/prompts", {"name": name, "persona": persona, "content": content})


@mcp.tool(annotations=AUTO_EXECUTABLE)
def evaluate_prompt(
    name: str, version: str, eval_cases: list[EvalCase], model: str = "claude-sonnet-5"
) -> dict:
    """Run the LLM-as-judge Evaluate Gate against a prompt version and report the pass rate."""
    return _post(
        f"/prompts/{name}/evaluate",
        {"version": version, "eval_cases": eval_cases, "model": model},
    )


@mcp.tool(annotations=NEEDS_CONFIRMATION)
def activate_prompt(name: str, version: str) -> dict:
    """Activate a prompt version for the chat endpoint — mutates live state."""
    return _post(f"/prompts/{name}/activate", {"version": version})


@mcp.tool(annotations=AUTO_EXECUTABLE)
def rag_ingest(
    collection: str, source_paths: list[str], chunk_size: int = 800, chunk_overlap: int = 100
) -> dict:
    """Chunk and embed documents into a Qdrant collection.

    Registers a new (inactive) RAG index version.
    """
    return _post(
        "/rag/ingest",
        {
            "collection": collection,
            "source_paths": source_paths,
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
        },
    )


@mcp.tool(annotations=AUTO_EXECUTABLE)
def rag_evaluate(
    collection: str,
    index_version: str,
    eval_cases: list[EvalCase],
    model: str = "claude-sonnet-5",
) -> dict:
    """Run the LLM-as-judge Evaluate Gate against a RAG index version and report the pass rate."""
    return _post(
        "/rag/evaluate",
        {
            "collection": collection,
            "index_version": index_version,
            "eval_cases": eval_cases,
            "model": model,
        },
    )


@mcp.tool(annotations=NEEDS_CONFIRMATION)
def rag_activate(collection: str, index_version: str) -> dict:
    """Activate a RAG index version for the chat endpoint — mutates live state."""
    return _post("/rag/activate", {"collection": collection, "index_version": index_version})


if __name__ == "__main__":
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "9002"))
    mcp.run(transport="streamable-http", host=host, port=port)
