"""Serving LLM API — deploys a self-hosted LLM (referenced by HuggingFace
Hub id, not an MLflow-registered artifact) as a KServe InferenceService via
vLLM. A separate router from models.py: prepare_deploy_manifest() there
hardcodes the MLflow Model Registry URI formula (`models:/{name}/{version}`)
twice over (once itself, once inside adapters/deploy_strategies.py's
InstantStrategy) — a raw HuggingFace LLM was never registered in MLflow, so
that formula doesn't apply here. No Evaluate Gate/policy-check step either:
an off-the-shelf LLM's weights don't change, there's no metric to compare
against a threshold the way a trained model has.

`Depends(get_current_user)` on the one route here — called by a Backstage
Custom Scaffolder Action, same as every route in models.py except
`/models/register`.
"""

from pathlib import Path
from typing import Final

from auth.keycloak import get_current_user
from fastapi import APIRouter, Depends
from jinja2 import Environment, FileSystemLoader
from kubernetes.client.exceptions import ApiException
from llm_serving.registry import (
    VLLM_QUANTIZATION_ARGS,
    get_llm_serving_runtime,
    validate_gpu_quantization,
)
from pydantic import BaseModel

from adapters.deploy_strategies import DirectStrategy, PRGatedStrategy, TrafficSplitStrategy
from adapters.interfaces import IDeployTrafficStrategy
from adapters.kserve_adapter import KServeAdapter

router = APIRouter(tags=["llm-serving"])

_TEMPLATES_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "templates"
_JINJA_ENV: Final[Environment] = Environment(loader=FileSystemLoader(_TEMPLATES_DIR))


class PrepareLlmDeployRequest(BaseModel):
    model_name: str
    huggingface_model_id: str
    runtime: str = "vllm"
    gpu_type: str
    gpu_count: int = 1
    quantization: str = "none"
    max_context_length: int = 4096
    # "direct" | "canary" | "ab" | "blue-green" — same shape as
    # models.py's PrepareDeployRequest, canary/ab/blue-green all render the
    # same canaryTrafficPercent field.
    traffic_strategy: str = "direct"
    traffic_percent: int | None = None
    # "pr-gated" | "instant"
    release_strategy: str = "pr-gated"


class PrepareLlmDeployResponse(BaseModel):
    file_name: str
    content: str
    deployed: bool = False


@router.post("/llm-deploy/prepare", response_model=PrepareLlmDeployResponse)
def prepare_llm_deploy_manifest(
    request: PrepareLlmDeployRequest, user: dict = Depends(get_current_user)
) -> PrepareLlmDeployResponse:
    validate_gpu_quantization(request.gpu_type, request.quantization)
    runtime_spec = get_llm_serving_runtime(request.runtime)
    vllm_quantization = VLLM_QUANTIZATION_ARGS.get(request.quantization)

    # Constructed lazily, only when actually needed — KServeAdapter.__init__
    # calls config.load_kube_config() eagerly, same reasoning as
    # models.py::prepare_deploy_manifest().
    needs_kserve = request.traffic_strategy != "direct" or request.release_strategy == "instant"
    kserve_adapter = KServeAdapter() if needs_kserve else None

    traffic_strategy: IDeployTrafficStrategy
    if request.traffic_strategy == "direct":
        traffic_strategy = DirectStrategy()
    else:
        assert kserve_adapter is not None
        try:
            kserve_adapter.get_inference_status(request.model_name)
        except ApiException as exc:
            if exc.status != 404:
                raise
            raise ValueError(
                f"{request.model_name} has no prior deploy — "
                "choose deployStrategy=direct for a model's first deploy"
            ) from exc
        if request.traffic_percent is None:
            raise ValueError("traffic_percent is required when traffic_strategy is not 'direct'")
        traffic_strategy = TrafficSplitStrategy(request.traffic_percent)

    traffic_fields = traffic_strategy.render()
    template = _JINJA_ENV.get_template("llm_inference_service.yaml.j2")
    content = template.render(
        model_name=request.model_name,
        model_version="1",
        huggingface_model_id=request.huggingface_model_id,
        serving_runtime_name=runtime_spec.serving_runtime_name,
        gpu_count=request.gpu_count,
        vllm_quantization=vllm_quantization,
        max_context_length=request.max_context_length,
        canary_traffic_percent=traffic_fields.get("canaryTrafficPercent"),
    )
    file_name = f"infra/inference-services/{request.model_name}/llm.yaml"

    if request.release_strategy == "instant":
        assert kserve_adapter is not None
        kserve_adapter.deploy_llm_model(
            request.model_name,
            "1",
            request.huggingface_model_id,
            runtime_spec.serving_runtime_name,
            request.gpu_count,
            vllm_quantization,
            request.max_context_length,
            traffic_fields=traffic_fields,
        )
        deployed = True
    else:
        # PRGatedStrategy.release() is a no-op ({"deployed": False}) that
        # doesn't touch model_name/model_version/manifest_content — safe to
        # reuse unchanged, same as models.py does.
        deployed = PRGatedStrategy().release(request.model_name, "1", content)["deployed"]

    return PrepareLlmDeployResponse(file_name=file_name, content=content, deployed=deployed)
