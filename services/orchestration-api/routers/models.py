"""Model Registry / Training / Deploy-prep API — the HTTP surface Golden Path
#1 (Train -> Track -> Register) and #2 (Register -> Deploy) drive.

Callers are deliberately mixed, unlike chat.py/prompts.py:
- `/trigger-training*`, `/models` (list), `/policy-check`, `/deploy-model/*`
  are called by Backstage Custom Scaffolder Actions (packages/backend).
- `POST /models/register` is called by the `register-step` container running
  *inside* an Argo workflow pod (see infra/argo-workflows/), not from
  Backstage — it has no Keycloak user session, so (like this whole router)
  it is intentionally left without a `Depends(get_current_user)` guard.

Business logic lives here, not in Backstage (CLAUDE.md) — this router only
orchestrates calls into the Adapter layer (adapters/mlflow_adapter.py,
adapters/argo_adapter.py) plus the Evaluate Gate (evaluations/).
"""

from pathlib import Path
from typing import Final

import pandas as pd
from data_quality.checks import CheckResult
from data_quality.registry import run_checks
from evaluations.gate import evaluate_metrics_gate
from fastapi import APIRouter
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel

from adapters.argo_adapter import ArgoAdapter
from adapters.mlflow_adapter import MlflowAdapter

router = APIRouter(tags=["models"])

# Module-level singletons — same convention as agents/mcp-servers/mlops-server/server.py.
mlflow_adapter = MlflowAdapter()
argo_adapter = ArgoAdapter()

# Single Argo WorkflowTemplate (infra/argo-workflows/train-register-template.yaml)
# now covers both train and fine-tune — mode is a workflow parameter, not a
# choice between two near-duplicate templates.
TRAIN_REGISTER_TEMPLATE: Final[str] = "train-register-golden-path"

_TEMPLATES_DIR: Final[Path] = Path(__file__).resolve().parent.parent / "templates"
_JINJA_ENV: Final[Environment] = Environment(loader=FileSystemLoader(_TEMPLATES_DIR))


class TriggerTrainingRequest(BaseModel):
    model_name: str
    dataset_uri: str
    task_type: str
    algorithm: str
    target_column: str | None = None
    id_columns: list[str] | None = None
    time_column: str | None = None
    base_model_uri: str | None = None


class TriggerTrainingResponse(BaseModel):
    workflow_name: str


class ValidateDatasetRequest(BaseModel):
    dataset_uri: str
    task_type: str
    target_column: str | None = None
    time_column: str | None = None


class CheckResultResponse(BaseModel):
    check_name: str
    severity: str
    message: str
    details: dict[str, object]

    @classmethod
    def from_check_result(cls, result: CheckResult) -> "CheckResultResponse":
        return cls(
            check_name=result.check_name,
            severity=result.severity,
            message=result.message,
            details=result.details,
        )


class WorkflowStatusResponse(BaseModel):
    name: str
    phase: str | None
    message: str | None


class WorkflowSummary(BaseModel):
    name: str | None
    phase: str | None
    started_at: str | None


class RegisterModelRequest(BaseModel):
    name: str
    artifact_uri: str
    task_type: str
    dataset_version: str | None = None


class RegisterModelResponse(BaseModel):
    name: str
    version: str


class ModelSummary(BaseModel):
    name: str
    version: str
    metrics: dict[str, float]
    tags: dict[str, str]


class ModelVersionSummaryResponse(BaseModel):
    name: str
    version: str
    task_type: str | None
    metrics: dict[str, float]
    tags: dict[str, str]


class LatestVersionResponse(BaseModel):
    name: str
    version: str


class PolicyCheckRequest(BaseModel):
    model_name: str
    model_version: str


class PrepareDeployRequest(BaseModel):
    model_name: str
    model_version: str


class PrepareDeployResponse(BaseModel):
    file_name: str
    content: str


class RecordDeployRequest(BaseModel):
    model_name: str
    model_version: str
    pr_url: str


class RecordDeployResponse(BaseModel):
    model_name: str
    model_version: str
    pr_url: str


@router.post("/trigger-training", response_model=TriggerTrainingResponse)
def trigger_training(request: TriggerTrainingRequest) -> TriggerTrainingResponse:
    parameters = {
        "model-name": request.model_name,
        "dataset-uri": request.dataset_uri,
        "task-type": request.task_type,
        "algorithm": request.algorithm,
        "mode": "finetune" if request.base_model_uri is not None else "train",
    }
    if request.target_column is not None:
        parameters["target-column"] = request.target_column
    if request.id_columns:
        parameters["id-columns"] = ",".join(request.id_columns)
    if request.time_column is not None:
        parameters["time-column"] = request.time_column
    if request.base_model_uri is not None:
        parameters["base-model-uri"] = request.base_model_uri
    result = argo_adapter.trigger_workflow(TRAIN_REGISTER_TEMPLATE, parameters)
    return TriggerTrainingResponse(workflow_name=result["metadata"]["name"])


@router.get("/trigger-training/{workflow_name}/status", response_model=WorkflowStatusResponse)
def get_training_status(workflow_name: str) -> WorkflowStatusResponse:
    status = argo_adapter.get_workflow_status(workflow_name)
    return WorkflowStatusResponse(**status)


@router.get("/trigger-training/recent", response_model=list[WorkflowSummary])
def list_recent_training_runs() -> list[WorkflowSummary]:
    return [
        WorkflowSummary(name=w.get("name"), phase=w.get("phase"), started_at=w.get("startedAt"))
        for w in argo_adapter.list_workflows()
    ]


@router.post("/models/register", response_model=RegisterModelResponse)
def register_model(request: RegisterModelRequest) -> RegisterModelResponse:
    result = mlflow_adapter.register_model(
        request.name, request.artifact_uri, request.dataset_version
    )
    # Tagged separately (not an IModelRegistryAdapter.register_model() param)
    # so policy_check() can read it back at deploy time without Backstage
    # having to resend taskType (mục 3.3).
    mlflow_adapter.set_model_version_tag(
        result["name"], result["version"], "task_type", request.task_type
    )
    return RegisterModelResponse(**result)


@router.post("/datasets/validate", response_model=list[CheckResultResponse])
def validate_dataset(request: ValidateDatasetRequest) -> list[CheckResultResponse]:
    csv_path = Path(request.dataset_uri.removeprefix("file://"))
    df = pd.read_csv(csv_path)
    results = run_checks(df, request.task_type, request.target_column, request.time_column)
    return [CheckResultResponse.from_check_result(r) for r in results]


@router.get("/models/{name}/{version}/summary", response_model=ModelVersionSummaryResponse)
def get_model_version_summary(name: str, version: str) -> ModelVersionSummaryResponse:
    details = mlflow_adapter.get_model_version_details(name, version)
    return ModelVersionSummaryResponse(
        name=name,
        version=details["version"],
        task_type=details["tags"].get("task_type"),
        metrics=details["metrics"],
        tags=details["tags"],
    )


@router.get("/models", response_model=list[ModelSummary])
def list_models() -> list[ModelSummary]:
    summaries: list[ModelSummary] = []
    for model in mlflow_adapter.list_models():
        name = model["name"]
        try:
            version = mlflow_adapter.get_latest_version(name)
        except ValueError:
            # Registered with zero versions yet (e.g. mid-training) — skip
            # rather than failing the whole Dashboard listing.
            continue
        details = mlflow_adapter.get_model_version_details(name, version)
        summaries.append(
            ModelSummary(
                name=name,
                version=details["version"],
                metrics=details["metrics"],
                tags=details["tags"],
            )
        )
    return summaries


@router.get("/models/{name}/latest-version", response_model=LatestVersionResponse)
def get_latest_version(name: str) -> LatestVersionResponse:
    return LatestVersionResponse(name=name, version=mlflow_adapter.get_latest_version(name))


@router.post("/policy-check")
def policy_check(request: PolicyCheckRequest) -> dict[str, object]:
    # Classical ML models have ground-truth metrics — compare them directly
    # against thresholds instead of routing through LLM-as-judge (no LiteLLM
    # cost). LLM/RAG artifacts still use evaluate_gate() (evaluations/gate.py).
    details = mlflow_adapter.get_model_version_details(request.model_name, request.model_version)
    task_type = details["tags"].get("task_type")
    if task_type is None:
        raise ValueError(
            f"model version {request.model_name}:{request.model_version} has no task_type tag "
            "— it was registered before task-type tagging was added"
        )
    gate_result = evaluate_metrics_gate(task_type, details["metrics"])

    # MLflow tags are strings — stringify every value before persisting.
    mlflow_adapter.set_model_version_tag(
        request.model_name, request.model_version, "gate_passed", str(gate_result["passed"])
    )
    for metric_name, value in details["metrics"].items():
        mlflow_adapter.set_model_version_tag(
            request.model_name, request.model_version, f"gate_{metric_name}", str(value)
        )
    return gate_result


@router.post("/deploy-model/prepare", response_model=PrepareDeployResponse)
def prepare_deploy_manifest(request: PrepareDeployRequest) -> PrepareDeployResponse:
    # Canonical MLflow Model Registry URI — resolvable by any MLflow-aware
    # loader (mlflow.pyfunc.load_model, KServe's "mlflow" modelFormat) without
    # needing the run's underlying artifact path.
    storage_uri = f"models:/{request.model_name}/{request.model_version}"
    template = _JINJA_ENV.get_template("inference_service.yaml.j2")
    content = template.render(
        model_name=request.model_name,
        model_version=request.model_version,
        storage_uri=storage_uri,
    )
    file_name = f"infra/inference-services/{request.model_name}/{request.model_version}.yaml"
    return PrepareDeployResponse(file_name=file_name, content=content)


@router.post("/deploy-model/record", response_model=RecordDeployResponse)
def record_deploy(request: RecordDeployRequest) -> RecordDeployResponse:
    mlflow_adapter.set_model_version_tag(
        request.model_name, request.model_version, "deploy_pr_url", request.pr_url
    )
    return RecordDeployResponse(
        model_name=request.model_name,
        model_version=request.model_version,
        pr_url=request.pr_url,
    )
