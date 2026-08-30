"""Discovers MCP servers by querying the Backstage Software Catalog's REST
API for `API, type: mcp` entities and reading their `mcp/endpoint`/
`mcp/transport` annotations — instead of a hardcoded local subprocess path
(see agents/mcp-servers/*/server.py and examples/entities.yaml).

Backstage's new-backend-system rejects unauthenticated calls to
`/api/catalog/entities` (verified against a live instance: 401
AuthenticationError) — a static service token
(`settings.backstage_service_token`, matching app-config.yaml's
`backend.auth.keys`) is required for this to actually return entities.
"""

import logging
from typing import TypedDict

import httpx
from core.config import settings

logger = logging.getLogger("orchestration_api.catalog_client")


class McpServerInfo(TypedDict):
    name: str
    endpoint: str
    transport: str


def discover_mcp_servers() -> list[McpServerInfo]:
    """Query the Catalog for `API, type: mcp` entities and return their
    connection info.

    Never raises — the Catalog or Backstage being unreachable must not
    prevent orchestration-api from starting; tool-calling just becomes
    unavailable (an empty list) instead.
    """
    headers = {}
    if settings.backstage_service_token:
        headers["Authorization"] = f"Bearer {settings.backstage_service_token}"

    try:
        response = httpx.get(
            f"{settings.backstage_base_url}/api/catalog/entities",
            params={"filter": "kind=api,spec.type=mcp"},
            headers=headers,
            timeout=10,
        )
        response.raise_for_status()
        entities = response.json()
    except Exception:
        logger.warning("Backstage Catalog unreachable — MCP discovery skipped", exc_info=True)
        return []

    servers: list[McpServerInfo] = []
    for entity in entities:
        metadata = entity.get("metadata", {})
        annotations = metadata.get("annotations", {})
        name = metadata.get("name", "unknown")
        endpoint = annotations.get("mcp/endpoint")
        transport = annotations.get("mcp/transport")
        if not endpoint or not transport:
            logger.warning(
                "Catalog entity %s missing mcp/endpoint or mcp/transport annotation, skipping",
                name,
            )
            continue
        servers.append({"name": name, "endpoint": endpoint, "transport": transport})

    return servers
