"""Chat API — routes requests to an LLM (Claude, or any model registered in
infra/llm-gateways/litellm-config.yaml, including a self-hosted model
deployed via the Serving LLM Golden Path) via the LLM Gateway, using the
persona's active system prompt and, optionally, RAG retrieval from an
active index. See docs/llmops-lifecycle-plan.md mục 9.4.

MCP tool-routing (use_tools=True) lets the Agent call the LLMOps Lifecycle
Golden Path tools (mcp_client.py, discovered via catalog_client.py) inside
a chat turn — bounded to one tool call and one follow-up model call, no
further looping. `activate_prompt`/`rag_activate` are never auto-executed:
LLMOps activation has no PR-gate (unlike MLOps), so a tool tagged
destructive_hint=True is only ever proposed, never called, until the user
explicitly confirms in a follow-up turn.
"""

import json
from typing import Final

from auth.keycloak import get_current_user
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from adapters.llm_gateway_adapter import LiteLLMGatewayAdapter
from adapters.vector_db_adapter import QdrantAdapter
from adapters.version_registry_adapter import JsonFileVersionRegistryAdapter

router = APIRouter(prefix="/chat", tags=["chat"])

llm_gateway_adapter = LiteLLMGatewayAdapter()
vector_store_adapter = QdrantAdapter()
registry_adapter = JsonFileVersionRegistryAdapter()

EMBEDDING_MODEL: Final[str] = "voyage-3"


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None
    persona: str = "mlops"
    use_rag: bool = False
    rag_collection: str | None = None
    # Lets the Agent call MCP tools (mcp_client.py) inside this turn — see
    # module docstring for the confirmation-gate behavior on destructive tools.
    use_tools: bool = False
    # Overridable — same reasoning as routers/rag.py's RagEvaluateRequest.model:
    # a hardcoded model= here would lock every chat to Claude regardless of
    # what's registered in litellm-config.yaml.
    model: str = "claude-sonnet-5"


class ChatResponse(BaseModel):
    reply: str
    persona_version: str
    rag_index_version: str | None = None
    # None when the model has no cost entry in litellm-config.yaml (e.g. a
    # self-hosted model via the Serving LLM Golden Path).
    tokens: int
    cost_usd: float | None
    # Names of tools actually executed this turn — empty unless use_tools=True
    # and the model called a non-destructive tool.
    tools_used: list[str] = []
    # Set instead of executing when the model wants to call a tool tagged
    # destructive_hint=True — the reply already explains the proposal; the
    # caller must send a new chat turn to actually confirm and act on it.
    pending_confirmation: str | None = None


@router.post("", response_model=ChatResponse)
async def send_message(
    chat_request: ChatRequest, http_request: Request, user: dict = Depends(get_current_user)
) -> ChatResponse:
    active_version = registry_adapter.get_active_version("prompt", chat_request.persona)
    if active_version is None:
        raise HTTPException(404, f"no active prompt version for persona {chat_request.persona!r}")
    system_prompt = registry_adapter.get_version("prompt", chat_request.persona, active_version)[
        "content"
    ]

    rag_version: str | None = None
    if chat_request.use_rag:
        if chat_request.rag_collection is None:
            raise HTTPException(400, "rag_collection is required when use_rag=True")
        rag_version = registry_adapter.get_active_version("rag-index", chat_request.rag_collection)
        if rag_version is None:
            raise HTTPException(
                400, f"no active RAG index for collection {chat_request.rag_collection!r}"
            )
        query_vector = llm_gateway_adapter.embed(EMBEDDING_MODEL, [chat_request.message])[0]
        hits = vector_store_adapter.search(query_vector, collection=chat_request.rag_collection)
        context = "\n\n".join(str(hit["payload"]["text"]) for hit in hits)
        system_prompt = f"Context:\n\n{context}\n\n{system_prompt}"

    messages: list[dict] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": chat_request.message},
    ]

    tools_used: list[str] = []
    pending_confirmation: str | None = None

    if chat_request.use_tools:
        registry = http_request.app.state.mcp_registry
        response = llm_gateway_adapter.chat_completion(
            model=chat_request.model, messages=messages, tools=registry.list_tools()
        )
        message = response["choices"][0]["message"]
        tool_calls = message.get("tool_calls") or []

        if tool_calls:
            # Bounded to 1 tool call per turn — avoids an unbounded
            # tool-call loop and keeps LLM cost/latency predictable.
            call = tool_calls[0]
            tool_name = call["function"]["name"]
            tool_args = json.loads(call["function"]["arguments"])

            if registry.is_destructive(tool_name):
                pending_confirmation = (
                    f"I'd like to call '{tool_name}' with {tool_args} — this "
                    "changes live state and needs your explicit confirmation "
                    "before I execute it."
                )
                return ChatResponse(
                    reply=pending_confirmation,
                    persona_version=active_version,
                    rag_index_version=rag_version,
                    tokens=(response.get("usage") or {}).get("total_tokens", 0),
                    cost_usd=response.get("response_cost_usd"),
                    tools_used=[],
                    pending_confirmation=pending_confirmation,
                )

            tool_result = await registry.call_tool(tool_name, tool_args)
            tools_used.append(tool_name)
            messages.append(message)
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": tool_result})
            response = llm_gateway_adapter.chat_completion(
                model=chat_request.model, messages=messages
            )
    else:
        response = llm_gateway_adapter.chat_completion(model=chat_request.model, messages=messages)

    reply = response["choices"][0]["message"]["content"]
    tokens = (response.get("usage") or {}).get("total_tokens", 0)
    return ChatResponse(
        reply=reply,
        persona_version=active_version,
        rag_index_version=rag_version,
        tokens=tokens,
        cost_usd=response.get("response_cost_usd"),
        tools_used=tools_used,
        pending_confirmation=pending_confirmation,
    )
