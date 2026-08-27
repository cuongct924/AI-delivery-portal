"""Concrete IDeployTrafficStrategy / IReleaseStrategy implementations for
Golden Path #2 (mục 4, docs/mlops-lifecycle-software-template.md). Kept in
one file — 4 small, tightly related classes, not worth 4 separate files.
"""

from dataclasses import dataclass

from adapters.interfaces import IDeployTrafficStrategy, IInferenceAdapter, IReleaseStrategy


class DirectStrategy(IDeployTrafficStrategy):
    """100% immediately — Knative Serving already avoids downtime via
    readiness-gated pod replacement, no extra field needed."""

    def render(self) -> dict:
        return {}


@dataclass(frozen=True)
class TrafficSplitStrategy(IDeployTrafficStrategy):
    """Canary/A-B/Blue-Green — same `canaryTrafficPercent` mechanism, the
    presets only differ in which percent the Dev-facing form suggests by
    default (mục 4.1: "1 strategy kỹ thuật, không phải 3 cơ chế riêng")."""

    percent: int

    def render(self) -> dict:
        return {"canaryTrafficPercent": self.percent}


class PRGatedStrategy(IReleaseStrategy):
    """Existing behavior, unchanged — a no-op. The caller (routers/models.py)
    still returns manifest_content for the Scaffolder Action to publish as
    a PR, same as before this strategy existed."""

    def release(self, model_name: str, model_version: str, manifest_content: str) -> dict:
        del model_name, model_version, manifest_content
        return {"deployed": False}


class InstantStrategy(IReleaseStrategy):
    """Calls the inference adapter directly — no Git/PR."""

    def __init__(self, inference_adapter: IInferenceAdapter, traffic_fields: dict | None = None):
        self.inference_adapter = inference_adapter
        self.traffic_fields = traffic_fields or {}

    def release(self, model_name: str, model_version: str, manifest_content: str) -> dict:
        del manifest_content  # unused — KServeAdapter renders its own body
        # Canonical MLflow Model Registry URI — same formula routers/models.py
        # already uses to build the Jinja2-rendered manifest's storageUri.
        storage_uri = f"models:/{model_name}/{model_version}"
        self.inference_adapter.deploy_model(
            model_name, model_version, storage_uri, traffic_fields=self.traffic_fields
        )
        return {"deployed": True}
