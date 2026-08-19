"""Receives chat requests from the UI, routing them to the AI LLM (Claude) via MCP tools."""

from auth.keycloak import get_current_user
from fastapi import APIRouter, Depends
from pydantic import BaseModel

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    reply: str


@router.post("", response_model=ChatResponse)
def send_message(request: ChatRequest, user: dict = Depends(get_current_user)) -> ChatResponse:
    # TODO: call Claude (anthropic SDK) and route tool-calls to the MCP servers
    # in agents/mcp-servers/*. See docs/architecture.md.
    return ChatResponse(reply=f"[stub] {user['preferred_username']} received: {request.message}")
