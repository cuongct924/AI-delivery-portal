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


# Only vLLM today — the registry exists so a second runtime (e.g. SGLang,
# which exposes the same OpenAI-compatible server shape) is a new entry,
# not a rewrite. Not pre-populated with runtimes that have no confirmed
# need yet (same call as dropping lightfm rather than half-supporting it).
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


# Which quantization schemes each GPU architecture supports for vLLM,
# confirmed against vLLM's own hardware-support docs (not assumed) — Ampere
# (A100) lacks full FP8 W8A8 compute (weight-only FP8 only, via Marlin
# kernels), Blackwell (B200) drops INT8 (unsupported at compute
# capability >= 10.0). Checked server-side, not just in the Scaffolder
# form's JSON Schema — the form narrows the enum for UX, this is the
# actual enforcement (CLAUDE.md: business logic lives in orchestration-api).
GPU_QUANTIZATION_COMPATIBILITY: Final[dict[str, frozenset[str]]] = {
    "L4": frozenset({"none", "fp8", "int8", "int4-awq"}),
    "L40S": frozenset({"none", "fp8", "int8", "int4-awq"}),
    "A100": frozenset({"none", "int8", "int4-awq"}),
    "H100": frozenset({"none", "fp8", "int8", "int4-awq"}),
    "H200": frozenset({"none", "fp8", "int8", "int4-awq"}),
    "B200": frozenset({"none", "fp8", "int4-awq"}),
}


# Dev-facing quantization label -> vLLM's own `--quantization` CLI value.
# "none" has no entry — vLLM auto-detects an unquantized checkpoint, the
# flag is omitted entirely rather than passed as "none" (see
# adapters/kserve_adapter.py's deploy_llm_model()). "int8" is mapped
# best-effort (compressed-tensors/LLM-Compressor int8 W8A8 checkpoints are
# normally auto-detected from the model's own config rather than needing
# an explicit value) — verify against the specific model chosen at deploy
# time, this mapping isn't independently confirmed the way the GPU
# compatibility matrix above is.
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
