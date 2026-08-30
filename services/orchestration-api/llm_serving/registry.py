"""Registry of self-hosted LLM serving runtimes, plus the GPU/quantization
compatibility matrix — same registry-by-dimension pattern as
infra/argo-workflows/training-image/dl_architecture_registry.py, keyed by
runtime name instead of DL architecture.
"""

from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class LLMServingRuntimeSpec:
    """One registry entry.

    Attributes:
        serving_runtime_name: Name of the KServe ServingRuntime CR this
            runtime maps to (see infra/llm-serving/README.md).
    """

    serving_runtime_name: str


# Only vLLM today — a second runtime is a new entry, not a rewrite.
LLM_SERVING_RUNTIMES: Final[dict[str, LLMServingRuntimeSpec]] = {
    "vllm": LLMServingRuntimeSpec(serving_runtime_name="vllm-runtime"),
}


def get_llm_serving_runtime(runtime: str) -> LLMServingRuntimeSpec:
    """Looks up a registry entry.

    Args:
        runtime: Currently only "vllm".

    Returns:
        The matching LLMServingRuntimeSpec.

    Raises:
        ValueError: runtime isn't in the registry.
    """
    spec = LLM_SERVING_RUNTIMES.get(runtime)
    if spec is None:
        raise ValueError(
            f"unknown runtime {runtime!r} — must be one of {sorted(LLM_SERVING_RUNTIMES)}"
        )
    return spec


# Per vLLM's hardware docs: A100 lacks full FP8 W8A8, B200 drops INT8.
# Enforced server-side, not just in the Scaffolder form's JSON Schema.
GPU_QUANTIZATION_COMPATIBILITY: Final[dict[str, frozenset[str]]] = {
    "L4": frozenset({"none", "fp8", "int8", "int4-awq"}),
    "L40S": frozenset({"none", "fp8", "int8", "int4-awq"}),
    "A100": frozenset({"none", "int8", "int4-awq"}),
    "H100": frozenset({"none", "fp8", "int8", "int4-awq"}),
    "H200": frozenset({"none", "fp8", "int8", "int4-awq"}),
    "B200": frozenset({"none", "fp8", "int4-awq"}),
}


# Dev-facing label -> vLLM's --quantization CLI value. "none" has no entry
# (flag omitted, auto-detected). "int8" is best-effort, unlike the
# GPU matrix above — verify against the actual model at deploy time.
VLLM_QUANTIZATION_ARGS: Final[dict[str, str]] = {
    "fp8": "fp8",
    "int8": "int8",
    "int4-awq": "awq",
}


def validate_gpu_quantization(gpu_type: str, quantization: str) -> None:
    """Rejects a GPU/quantization combination vLLM can't actually run.

    Args:
        gpu_type: One of GPU_QUANTIZATION_COMPATIBILITY's keys.
        quantization: The requested quantization scheme.

    Raises:
        ValueError: gpu_type is unknown, or doesn't support quantization.
    """
    supported = GPU_QUANTIZATION_COMPATIBILITY.get(gpu_type)
    if supported is None:
        raise ValueError(
            f"unknown gpu_type {gpu_type!r} — must be one of "
            f"{sorted(GPU_QUANTIZATION_COMPATIBILITY)}"
        )
    if quantization not in supported:
        raise ValueError(
            f"{gpu_type} does not support quantization={quantization!r} — "
            f"valid options: {sorted(supported)}"
        )
