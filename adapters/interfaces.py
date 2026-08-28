"""Shared contract for every Adapter — implemented via the Adapter Pattern.

Principle: switching from Mock/MLflow to a real self-hosted backend only
requires adding one new class that implements this interface, without
touching code that already depends on the interface.
"""

from abc import ABC, abstractmethod


class IModelRegistryAdapter(ABC):
    @abstractmethod
    def register_model(self, name: str, artifact_uri: str) -> dict: ...

    @abstractmethod
    def list_models(self, project: str | None = None) -> list[dict]: ...

    @abstractmethod
    def get_model_metrics(self, name: str, version: str) -> dict: ...

    @abstractmethod
    def get_dataset_lineage(self, name: str, version: str) -> list[dict]: ...

    @abstractmethod
    def set_model_version_tag(self, name: str, version: str, key: str, value: str) -> None: ...

    @abstractmethod
    def get_model_version_details(self, name: str, version: str) -> dict: ...


class IInferenceAdapter(ABC):
    @abstractmethod
    def deploy_model(
        self, name: str, version: str, model_uri: str, traffic_fields: dict | None = None
    ) -> dict: ...

    @abstractmethod
    def get_inference_status(self, name: str) -> dict: ...

    @abstractmethod
    def predict(self, name: str, payload: dict) -> dict: ...


class IDeployTrafficStrategy(ABC):
    """How traffic moves to the new model version — Golden Path #2.

    Direct and TrafficSplit (Canary/A-B/Blue-Green) are the only 2
    concrete strategies: KServe's `canaryTrafficPercent` field is one
    mechanism that Canary/A-B/Blue-Green only differ in *intent* over —
    not 3 separate classes.
    """

    @abstractmethod
    def render(self) -> dict:
        """Fields to merge into the InferenceService's spec.predictor
        block — {} for Direct, {"canaryTrafficPercent": N} for TrafficSplit."""


class IReleaseStrategy(ABC):
    """How a deploy gets approved — PR-gated (default, unchanged) vs
    Instant (calls the inference adapter directly, no Git/PR)."""

    @abstractmethod
    def release(self, model_name: str, model_version: str, manifest_content: str) -> dict:
        """Performs the release action. PRGatedStrategy is a no-op — the
        caller still publishes manifest_content as a PR itself. Instant
        actually deploys and returns {"deployed": True}."""


class IWorkflowAdapter(ABC):
    @abstractmethod
    def trigger_workflow(self, template_name: str, parameters: dict) -> dict: ...

    @abstractmethod
    def get_workflow_status(self, workflow_name: str) -> dict: ...


class IVectorStoreAdapter(ABC):
    @abstractmethod
    def upsert(self, ids: list[str], vectors: list[list[float]], payloads: list[dict]) -> dict: ...

    @abstractmethod
    def search(self, query_vector: list[float], top_k: int = 5) -> list[dict]: ...


class ILLMGatewayAdapter(ABC):
    @abstractmethod
    def chat_completion(self, model: str, messages: list[dict], **kwargs) -> dict: ...

    @abstractmethod
    def list_models(self) -> list[dict]: ...


class IFeatureStoreAdapter(ABC):
    @abstractmethod
    def get_offline_features(
        self, entity_ids: list[str], feature_names: list[str], dataset_version: str | None = None
    ) -> list[dict]: ...

    @abstractmethod
    def get_online_features(self, entity_id: str, feature_names: list[str]) -> dict: ...


class INotebookAdapter(ABC):
    @abstractmethod
    def create_notebook(
        self, environment: str, ram_gb: int, gpu_type: str | None = None
    ) -> dict: ...

    @abstractmethod
    def get_notebook_status(self, notebook_id: str) -> dict: ...

    @abstractmethod
    def delete_notebook(self, notebook_id: str) -> dict: ...
