"""Tests adapters/argo_adapter.py — mocks httpx so no real Argo Server is required."""

from unittest.mock import MagicMock, patch

from adapters.argo_adapter import ArgoAdapter


def _mock_response(json_data: dict) -> MagicMock:
    response = MagicMock()
    response.json.return_value = json_data
    response.raise_for_status.return_value = None
    return response


def test_get_workflow_status_includes_message() -> None:
    adapter = ArgoAdapter(base_url="http://argo.test")
    response = _mock_response({"status": {"phase": "Failed", "message": "pod OOMKilled"}})

    with patch("adapters.argo_adapter.httpx.get", return_value=response) as mock_get:
        result = adapter.get_workflow_status("train-abc123")

    mock_get.assert_called_once_with(
        "http://argo.test/api/v1/workflows/default/train-abc123", timeout=10
    )
    assert result == {"name": "train-abc123", "phase": "Failed", "message": "pod OOMKilled"}


def test_get_workflow_status_message_defaults_to_none_when_absent() -> None:
    adapter = ArgoAdapter(base_url="http://argo.test")
    response = _mock_response({"status": {"phase": "Succeeded"}})

    with patch("adapters.argo_adapter.httpx.get", return_value=response):
        result = adapter.get_workflow_status("train-abc123")

    assert result["message"] is None


def test_list_workflows_extracts_name_phase_started_at() -> None:
    adapter = ArgoAdapter(base_url="http://argo.test")
    response = _mock_response(
        {
            "items": [
                {
                    "metadata": {"name": "train-abc123"},
                    "status": {"phase": "Succeeded", "startedAt": "2026-08-25T00:00:00Z"},
                },
                {
                    "metadata": {"name": "train-def456"},
                    "status": {"phase": "Running", "startedAt": "2026-08-25T00:05:00Z"},
                },
            ]
        }
    )

    with patch("adapters.argo_adapter.httpx.get", return_value=response) as mock_get:
        result = adapter.list_workflows()

    mock_get.assert_called_once_with("http://argo.test/api/v1/workflows/default", timeout=10)
    assert result == [
        {"name": "train-abc123", "phase": "Succeeded", "startedAt": "2026-08-25T00:00:00Z"},
        {"name": "train-def456", "phase": "Running", "startedAt": "2026-08-25T00:05:00Z"},
    ]


def test_list_workflows_returns_empty_list_when_no_items() -> None:
    adapter = ArgoAdapter(base_url="http://argo.test")
    response = _mock_response({})

    with patch("adapters.argo_adapter.httpx.get", return_value=response):
        result = adapter.list_workflows()

    assert result == []
