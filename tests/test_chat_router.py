"""services/orchestration-api/routers/chat.py — patches the module-level
`llm_gateway_adapter`/`vector_store_adapter`/`registry_adapter` singletons,
same pattern as tests/test_rag_router.py.
"""

from unittest.mock import patch

import pytest
from fastapi import HTTPException
from routers.chat import ChatRequest, send_message


def test_send_message_uses_active_prompt_and_forwards_model() -> None:
    request = ChatRequest(message="hi", persona="mlops", model="llama-3-8b-self-hosted")
    with (
        patch("routers.chat.registry_adapter") as mock_registry,
        patch("routers.chat.llm_gateway_adapter") as mock_gateway,
    ):
        mock_registry.get_active_version.return_value = "3"
        mock_registry.get_version.return_value = {"content": "system prompt"}
        mock_gateway.chat_completion.return_value = {
            "choices": [{"message": {"content": "hello"}}],
            "usage": {"total_tokens": 42},
            "response_cost_usd": 0.001,
        }

        response = send_message(request)

    assert response.reply == "hello"
    assert response.persona_version == "3"
    assert response.rag_index_version is None
    assert response.tokens == 42
    assert response.cost_usd == pytest.approx(0.001)
    mock_gateway.chat_completion.assert_called_once_with(
        model="llama-3-8b-self-hosted",
        messages=[
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "hi"},
        ],
    )


def test_send_message_raises_404_when_persona_has_no_active_version() -> None:
    request = ChatRequest(message="hi", persona="unknown-persona")
    with patch("routers.chat.registry_adapter") as mock_registry:
        mock_registry.get_active_version.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            send_message(request)
    assert exc_info.value.status_code == 404


def test_send_message_use_rag_without_collection_raises_400() -> None:
    request = ChatRequest(message="hi", use_rag=True, rag_collection=None)
    with patch("routers.chat.registry_adapter") as mock_registry:
        mock_registry.get_active_version.return_value = "1"
        with pytest.raises(HTTPException) as exc_info:
            send_message(request)
    assert exc_info.value.status_code == 400


def test_send_message_use_rag_without_active_index_raises_400() -> None:
    request = ChatRequest(message="hi", use_rag=True, rag_collection="smoke-test")
    with patch("routers.chat.registry_adapter") as mock_registry:
        mock_registry.get_active_version.side_effect = ["1", None]
        with pytest.raises(HTTPException) as exc_info:
            send_message(request)
    assert exc_info.value.status_code == 400


def test_send_message_use_rag_prepends_context_and_returns_index_version() -> None:
    request = ChatRequest(message="hi", use_rag=True, rag_collection="smoke-test")
    with (
        patch("routers.chat.registry_adapter") as mock_registry,
        patch("routers.chat.llm_gateway_adapter") as mock_gateway,
        patch("routers.chat.vector_store_adapter") as mock_vector_store,
    ):
        mock_registry.get_active_version.side_effect = ["1", "2"]  # prompt, then rag-index
        mock_registry.get_version.return_value = {"content": "system prompt"}
        mock_gateway.embed.return_value = [[0.1]]
        mock_vector_store.search.return_value = [{"payload": {"text": "retrieved chunk"}}]
        mock_gateway.chat_completion.return_value = {"choices": [{"message": {"content": "hello"}}]}

        response = send_message(request)

    assert response.rag_index_version == "2"
    mock_gateway.chat_completion.assert_called_once_with(
        model="claude-sonnet-5",
        messages=[
            {"role": "system", "content": "Context:\n\nretrieved chunk\n\nsystem prompt"},
            {"role": "user", "content": "hi"},
        ],
    )
