"""Dynamic MCP session manager — discovers MCP servers via catalog_client.py
(the Backstage Catalog, not a hardcoded local path) and keeps live
`ClientSession`s open for the app's lifetime, wired up once at FastAPI
startup (see main.py's lifespan).

Each server's connection runs in its own dedicated `asyncio.Task` rather
than sharing one `AsyncExitStack` across servers — verified live that
sharing a stack is unsafe here: `streamable_http_client`'s internal anyio
`TaskGroup` uses cancel scopes that must be entered and exited in the same
task, and one server's connection failure corrupted the shared stack's
ability to manage an already-successful entry for a different server. A
dedicated task per server keeps each connection's enter/exit within its own
task, which is what anyio actually requires.

Verified end-to-end during development: real Catalog discovery -> real
streamable-http MCP connection -> a real Golden Path tool call, with a
verified Keycloak identity on the orchestration-api side.
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
    calls to the right one.

    Every method that talks to a server degrades gracefully on failure — a
    server that can't be reached (or wasn't discovered at all) must never
    prevent orchestration-api from starting or from serving chat requests
    with `use_tools=False`.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, ClientSession] = {}
        self._tool_to_server: dict[str, str] = {}
        self._tools: dict[str, Tool] = {}
        self._tasks: list[asyncio.Task[None]] = []
        self._shutdown = asyncio.Event()

    async def connect_all(self) -> None:
        """Discover MCP servers via the Catalog and open a session to each,
        one dedicated task per server. Returns once every connection
        attempt has either succeeded or failed (not before)."""
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
        """True for tools (activate_prompt, rag_activate) that must go
        through a human confirmation step rather than being auto-called —
        LLMOps activation has no PR-gate, so this is the only safety gate."""
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
        """Owns one server's connection for the task's whole lifetime —
        enters the transport/session, publishes its tools, then blocks
        until `aclose()` signals shutdown, so exit happens in this same
        task too."""
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
            # Deliberately broad: verified live that a failed connection
            # here can surface as a plain Exception, a BaseExceptionGroup
            # (anyio TaskGroup wrapping a CancelledError, which is itself a
            # BaseException — `except Exception` doesn't catch it), or a
            # bare CancelledError propagated from the aborted transport.
            # This task's entire job is "isolate one server's failure so
            # every other server's task is unaffected" — re-raise only the
            # 2 signals that must always propagate.
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
