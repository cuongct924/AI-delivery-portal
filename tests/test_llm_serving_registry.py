"""services/orchestration-api/llm_serving/registry.py."""

import pytest
from llm_serving.registry import get_llm_serving_runtime, validate_gpu_quantization


def test_get_llm_serving_runtime_returns_vllm_spec() -> None:
    spec = get_llm_serving_runtime("vllm")
    assert spec.serving_runtime_name == "vllm-runtime"


def test_get_llm_serving_runtime_raises_for_unknown_runtime() -> None:
    with pytest.raises(ValueError, match=r"\['vllm'\]"):
        get_llm_serving_runtime("sglang")


def test_validate_gpu_quantization_allows_supported_combination() -> None:
    validate_gpu_quantization("H100", "fp8")  # does not raise


def test_validate_gpu_quantization_rejects_fp8_on_a100() -> None:
    with pytest.raises(ValueError, match="A100 does not support quantization='fp8'"):
        validate_gpu_quantization("A100", "fp8")


def test_validate_gpu_quantization_rejects_int8_on_b200() -> None:
    with pytest.raises(ValueError, match="B200 does not support quantization='int8'"):
        validate_gpu_quantization("B200", "int8")


def test_validate_gpu_quantization_raises_for_unknown_gpu_type() -> None:
    with pytest.raises(ValueError, match="unknown gpu_type"):
        validate_gpu_quantization("RTX4090", "none")
