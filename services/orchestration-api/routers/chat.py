"""Chat API — routes requests to an LLM (Claude, or any model registered in
infra/llm-gateways/litellm-config.yaml, including a self-hosted model
deployed via the Serving LLM Golden Path) via the LLM Gateway, using the
persona's active system prompt and, optionally, RAG retrieval from an
active index. See docs/llmops-lifecycle-plan.md mục 9.4.

MCP tool-routing (the TODO this file used to carry) is a separate,
not-yet-built "AI Agent copilot" capability, independent of prompt/RAG
version management — see docs/llmops-lifecycle-plan.md mục 7.
"""

from typing import Final

from auth.keycloak import get_current_user
from fastapi import APIRouter, Depends, HTTPException
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


@router.post("", response_model=ChatResponse)
def send_message(request: ChatRequest, user: dict = Depends(get_current_user)) -> ChatResponse:
    active_version = registry_adapter.get_active_version("prompt", request.persona)
    if active_version is None:
        raise HTTPException(404, f"no active prompt version for persona {request.persona!r}")
    system_prompt = registry_adapter.get_version("prompt", request.persona, active_version)[
        "content"
    ]

    rag_version: str | None = None
    if request.use_rag:
        if request.rag_collection is None:
            raise HTTPException(400, "rag_collection is required when use_rag=True")
        rag_version = registry_adapter.get_active_version("rag-index", request.rag_collection)
        if rag_version is None:
            raise HTTPException(
                400, f"no active RAG index for collection {request.rag_collection!r}"
            )
        query_vector = llm_gateway_adapter.embed(EMBEDDING_MODEL, [request.message])[0]
        hits = vector_store_adapter.search(query_vector, collection=request.rag_collection)
        context = "\n\n".join(str(hit["payload"]["text"]) for hit in hits)
        system_prompt = f"Context:\n\n{context}\n\n{system_prompt}"

    response = llm_gateway_adapter.chat_completion(
        model=request.model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.message},
        ],
    )
    reply = response["choices"][0]["message"]["content"]
    tokens = (response.get("usage") or {}).get("total_tokens", 0)
    return ChatResponse(
        reply=reply,
        persona_version=active_version,
        rag_index_version=rag_version,
        tokens=tokens,
        cost_usd=response.get("response_cost_usd"),
    )
