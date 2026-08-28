"""Prompt Registry API — manages versions of system prompts, kept fully
separate from the Model Registry (unlike traditional MLOps, see docs/architecture.md).
The Portal reads this data through the `plugins/prompt-registry/` plugin
(Backstage), via the `/orchestration-api` proxy declared in app-config.yaml.

Demo version: in-memory data. For production, replace with a DB (Postgres)
or Git to store each prompt's version history.
"""

from auth.keycloak import get_current_user
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/prompts", tags=["prompts"])


class PromptVersion(BaseModel):
    id: str
    name: str
    version: str
    persona: str
    content: str


_PROMPTS: list[PromptVersion] = [
    PromptVersion(
        id="mlops-v1",
        name="mlops",
        version="v1",
        persona="MLOps Assistant",
        content="You are the MLOps assistant for the AI Delivery Portal. You help "
        "ML engineers look up experiments, model registry entries, and deploy "
        "status via MCP tools.",
    ),
    PromptVersion(
        id="k8s-v1",
        name="k8s",
        version="v1",
        persona="K8s Assistant",
        content="You are the Kubernetes operations assistant. You may only read "
        "status (pods, logs, events) via MCP tools — you have no write/delete permission.",
    ),
]


@router.get("", response_model=list[PromptVersion])
def list_prompts(user: dict = Depends(get_current_user)) -> list[PromptVersion]:
    return _PROMPTS


@router.get("/{prompt_id}", response_model=PromptVersion)
def get_prompt(prompt_id: str, user: dict = Depends(get_current_user)) -> PromptVersion:
    for p in _PROMPTS:
        if p.id == prompt_id:
            return p
    raise HTTPException(404, f"Prompt not found: {prompt_id}")
