"""services/orchestration-api/routers/llm_serving.py — patches
`routers.llm_serving.get_kserve_adapter` and calls the route function
directly, same pattern as tests/test_models_router.py's
prepare_deploy_manifest tests. No mlflow stub needed — this router
doesn't import the mlflow SDK.
"""

from unittest.mock import patch

import pytest
from kubernetes.client.exceptions import ApiException
from routers.llm_serving import PrepareLlmDeployRequest, prepare_llm_deploy_manifest


def test_prepare_llm_deploy_manifest_renders_manifest_correctly() -> None:
    request = PrepareLlmDeployRequest(
        model_name="llama-3-8b",
        huggingface_model_id="meta-llama/Llama-3.1-8B-Instruct",
        gpu_type="H100",
    )

    response = prepare_llm_deploy_manifest(request)

    assert response.file_name == "infra/inference-services/llama-3-8b/llm.yaml"
    assert "name: llama-3-8b" in response.content
    assert 'version: "1"' in response.content
    assert "storageUri: hf://meta-llama/Llama-3.1-8B-Instruct" in response.content
    assert "--tensor-parallel-size=1" in response.content
    assert "--max-model-len=4096" in response.content
    assert "--quantization" not in response.content  # quantization="none" default
    assert "canaryTrafficPercent" not in response.content
    assert response.deployed is False


def test_prepare_llm_deploy_manifest_direct_never_touches_kserve() -> None:
    request = PrepareLlmDeployRequest(
        model_name="llama-3-8b",
        huggingface_model_id="meta-llama/Llama-3.1-8B-Instruct",
        gpu_type="H100",
    )
    with patch("routers.llm_serving.get_kserve_adapter") as mock_get_kserve:
        prepare_llm_deploy_manifest(request)
    mock_get_kserve.assert_not_called()


def test_prepare_llm_deploy_manifest_renders_quantization_arg() -> None:
    request = PrepareLlmDeployRequest(
        model_name="llama-3-8b",
        huggingface_model_id="meta-llama/Llama-3.1-8B-Instruct",
        gpu_type="H100",
        quantization="fp8",
    )

    response = prepare_llm_deploy_manifest(request)

    assert "--quantization=fp8" in response.content


def test_prepare_llm_deploy_manifest_traffic_split_renders_canary_percent() -> None:
    request = PrepareLlmDeployRequest(
        model_name="llama-3-8b",
        huggingface_model_id="meta-llama/Llama-3.1-8B-Instruct",
        gpu_type="H100",
        traffic_strategy="canary",
        traffic_percent=10,
    )
    with patch("routers.llm_serving.get_kserve_adapter") as mock_get_kserve:
        mock_get_kserve.return_value.get_inference_status.return_value = {"status": {}}
        response = prepare_llm_deploy_manifest(request)

    assert "canaryTrafficPercent: 10" in response.content
    assert response.deployed is False


def test_prepare_llm_deploy_manifest_traffic_split_without_prior_deploy_raises() -> None:
    request = PrepareLlmDeployRequest(
        model_name="never-deployed",
        huggingface_model_id="meta-llama/Llama-3.1-8B-Instruct",
        gpu_type="H100",
        traffic_strategy="canary",
        traffic_percent=10,
    )
    with patch("routers.llm_serving.get_kserve_adapter") as mock_get_kserve:
        mock_get_kserve.return_value.get_inference_status.side_effect = ApiException(status=404)
        with pytest.raises(ValueError, match="no prior deploy"):
            prepare_llm_deploy_manifest(request)


def test_prepare_llm_deploy_manifest_traffic_split_requires_percent() -> None:
    request = PrepareLlmDeployRequest(
        model_name="llama-3-8b",
        huggingface_model_id="meta-llama/Llama-3.1-8B-Instruct",
        gpu_type="H100",
        traffic_strategy="canary",
    )
    with patch("routers.llm_serving.get_kserve_adapter") as mock_get_kserve:
        mock_get_kserve.return_value.get_inference_status.return_value = {"status": {}}
        with pytest.raises(ValueError, match="traffic_percent is required"):
            prepare_llm_deploy_manifest(request)


def test_prepare_llm_deploy_manifest_instant_calls_deploy_llm_model() -> None:
    request = PrepareLlmDeployRequest(
        model_name="llama-3-8b",
        huggingface_model_id="meta-llama/Llama-3.1-8B-Instruct",
        gpu_type="H100",
        gpu_count=2,
        quantization="fp8",
        release_strategy="instant",
    )
    with patch("routers.llm_serving.get_kserve_adapter") as mock_get_kserve:
        response = prepare_llm_deploy_manifest(request)

    mock_get_kserve.return_value.deploy_llm_model.assert_called_once_with(
        "llama-3-8b",
        "1",
        "meta-llama/Llama-3.1-8B-Instruct",
        "vllm-runtime",
        2,
        "fp8",
        4096,
        traffic_fields={},
    )
    assert response.deployed is True


def test_prepare_llm_deploy_manifest_rejects_incompatible_gpu_quantization() -> None:
    request = PrepareLlmDeployRequest(
        model_name="llama-3-8b",
        huggingface_model_id="meta-llama/Llama-3.1-8B-Instruct",
        gpu_type="A100",
        quantization="fp8",
    )
    with (
        patch("routers.llm_serving.get_kserve_adapter") as mock_get_kserve,
        pytest.raises(ValueError, match="A100 does not support"),
    ):
        prepare_llm_deploy_manifest(request)
    mock_get_kserve.assert_not_called()
