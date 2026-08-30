"""services/orchestration-api/routers/prompts.py — calls the route functions
directly, no need for a FastAPI TestClient since we're not testing the HTTP/
routing layer. Backed by a real JsonFileVersionRegistryAdapter — tests/
conftest.py redirects LLMOPS_REGISTRY_PATH to a fresh temp file before any
router module imports, so _seed_default_prompts() (run at import time)
always starts from a clean slate for this test session."""

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from routers.prompts import (
    ActivatePromptRequest,
    DraftPromptRequest,
    EvaluatePromptRequest,
    PromptEvalCase,
    activate_prompt,
    draft_prompt,
    evaluate_prompt,
    get_prompt,
    list_prompts,
)


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


def test_draft_prompt_registers_a_new_unactivated_version():
    request = DraftPromptRequest(name="rag-writer", persona="RAG Writer", content="Draft content")
    response = draft_prompt(request)

    assert response.id == "rag-writer-v1"
    assert response.version == "1"
    # Not active — list_prompts() shouldn't surface a persona with no active version.
    assert "rag-writer" not in {p.name for p in list_prompts()}


def test_evaluate_prompt_computes_pass_rate_and_forwards_model():
    draft_prompt(DraftPromptRequest(name="eval-target", persona="Eval Target", content="sys"))
    request = EvaluatePromptRequest(
        version="1",
        eval_cases=[PromptEvalCase(question="q1"), PromptEvalCase(question="q2")],
        model="llama-3-8b-self-hosted",
    )
    with (
        patch("routers.prompts.llm_gateway_adapter") as mock_gateway,
        patch("routers.prompts.judge_response") as mock_judge,
        patch("routers.prompts.evaluate_gate") as mock_gate,
    ):
        mock_gateway.chat_completion.return_value = {
            "choices": [{"message": {"content": "an answer"}}],
            "usage": {"total_tokens": 100},
            "response_cost_usd": 0.002,
        }
        mock_judge.return_value = {"safety": 9, "correctness": 9, "relevance": 9}
        mock_gate.side_effect = [{"passed": True}, {"passed": True}]
        response = evaluate_prompt("eval-target", request)

    assert response.passed is True
    assert response.pass_rate == 1.0
    assert response.total_tokens == 200  # 100 per eval_case, 2 eval_cases
    assert response.total_cost_usd == pytest.approx(0.004)
    mock_gateway.chat_completion.assert_any_call(
        model="llama-3-8b-self-hosted",
        messages=[
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "q1"},
        ],
    )


def test_activate_prompt_makes_version_visible_in_list_prompts():
    draft_prompt(
        DraftPromptRequest(name="activate-target", persona="Activate Target", content="sys")
    )
    activate_prompt("activate-target", ActivatePromptRequest(version="1"))

    assert "activate-target" in {p.name for p in list_prompts()}


def test_activate_prompt_raises_for_unregistered_version():
    with pytest.raises(ValueError, match="no registered versions"):
        activate_prompt("never-drafted", ActivatePromptRequest(version="1"))
