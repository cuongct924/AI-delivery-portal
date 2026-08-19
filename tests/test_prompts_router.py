"""services/orchestration-api/routers/prompts.py — calls the route functions
directly, no need for a FastAPI TestClient since we're not testing the HTTP/
routing layer."""

import pytest
from fastapi import HTTPException
from routers.prompts import get_prompt, list_prompts


def test_list_prompts_returns_seeded_prompts():
    prompts = list_prompts()
    assert {p.name for p in prompts} == {"mlops", "k8s"}


def test_get_prompt_found():
    prompt = get_prompt("mlops-v1")
    assert prompt.persona == "MLOps Assistant"


def test_get_prompt_not_found_raises_404():
    with pytest.raises(HTTPException) as exc_info:
        get_prompt("does-not-exist")
    assert exc_info.value.status_code == 404
