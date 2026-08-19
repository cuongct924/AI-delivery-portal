"""Shared contract for every Adapter — implemented via the Adapter Pattern.

Principle: switching from Mock/MLflow to Viettel's real system only requires
adding one new class that implements this interface, without touching code
that already depends on the interface.
"""

from abc import ABC, abstractmethod


class IModelRegistryAdapter(ABC):
    @abstractmethod
    def register_model(self, name: str, version: str, artifact_uri: str) -> dict: ...

    @abstractmethod
    def list_models(self, project: str | None = None) -> list[dict]: ...

    @abstractmethod
    def get_model_metrics(self, name: str, version: str) -> dict: ...


class IInferenceAdapter(ABC):
    @abstractmethod
    def deploy_model(self, name: str, version: str, model_uri: str) -> dict: ...

    @abstractmethod
    def get_inference_status(self, name: str) -> dict: ...

    @abstractmethod
    def predict(self, name: str, payload: dict) -> dict: ...


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
