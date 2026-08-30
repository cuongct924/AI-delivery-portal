"""Dynamic MCP session manager — discovers MCP servers via the Backstage
Catalog (catalog_client.py) and keeps live sessions open for the app's
lifetime (see main.py's lifespan).

Each server connects in its own `asyncio.Task`: anyio cancel scopes must
enter/exit in the same task, so sharing one `AsyncExitStack` across servers
lets one failure corrupt another server's connection.
"""

import asyncio
import logging
from typing import Any, TypedDict

from catalog_client import McpServerInfo, discover_mcp_servers
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import TextContent, Tool

logger = logging.getLogger("orchestration_api.mcp_client")


class ToolSchema(TypedDict):
    type: str
    function: dict[str, Any]


class McpToolRegistry:
    """Holds live MCP sessions discovered via the Catalog and routes tool
    calls to the right one. Unreachable servers degrade gracefully, never
    block startup.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, ClientSession] = {}
        self._tool_to_server: dict[str, str] = {}
        self._tools: dict[str, Tool] = {}
        self._tasks: list[asyncio.Task[None]] = []
        self._shutdown = asyncio.Event()

    async def connect_all(self) -> None:
        """Connect to every discovered server; returns once each has
        succeeded or failed."""
        servers = discover_mcp_servers()
        ready_events = [asyncio.Event() for _ in servers]
        self._tasks = [
            asyncio.create_task(self._run_server(server, ready))
            for server, ready in zip(servers, ready_events, strict=True)
        ]
        if ready_events:
            await asyncio.gather(*(e.wait() for e in ready_events))

    def list_tools(self) -> list[ToolSchema]:
        """Tool schemas in the OpenAI-style `tools=[...]` shape
        `LiteLLMGatewayAdapter.chat_completion(tools=...)` expects."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description or "",
                    "parameters": tool.input_schema,
                },
            }
            for tool in self._tools.values()
        ]

    def is_destructive(self, tool_name: str) -> bool:
        """True for tools that need human confirmation, not auto-calling."""
        tool = self._tools.get(tool_name)
        return bool(tool and tool.annotations and tool.annotations.destructive_hint)

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        server_name = self._tool_to_server.get(tool_name)
        if server_name is None:
            raise ValueError(f"Unknown tool: {tool_name}")
        session = self._sessions[server_name]
        result = await session.call_tool(tool_name, arguments)
        if not result.content:
            return ""
        first = result.content[0]
        return first.text if isinstance(first, TextContent) else str(first)

    async def aclose(self) -> None:
        self._shutdown.set()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

    async def _run_server(self, server: McpServerInfo, ready: asyncio.Event) -> None:
        """Owns one server's connection until `aclose()` signals shutdown."""
        if server["transport"] != "streamable-http":
            logger.warning(
                "Unsupported MCP transport %s for %s, skipping",
                server["transport"],
                server["name"],
            )
            ready.set()
            return

        try:
            async with (
                streamable_http_client(server["endpoint"]) as (read, write),
                ClientSession(read, write) as session,
            ):
                await session.initialize()
                tools = await session.list_tools()

                self._sessions[server["name"]] = session
                for tool in tools.tools:
                    self._tool_to_server[tool.name] = server["name"]
                    self._tools[tool.name] = tool
                logger.info(
                    "Connected to MCP server %s (%d tools)", server["name"], len(tools.tools)
                )
                ready.set()

                await self._shutdown.wait()
        except BaseException as exc:
            # Broad on purpose: a failed connection can raise a
            # BaseExceptionGroup, not just Exception.
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            logger.warning(
                "Could not connect to / lost connection to MCP server %s at %s",
                server["name"],
                server["endpoint"],
                exc_info=True,
            )
        finally:
            ready.set()
            self._sessions.pop(server["name"], None)
