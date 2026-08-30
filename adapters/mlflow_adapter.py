"""Real adapter using the MLflow SDK — connects to the mlflow service in docker-compose.yml."""

import os

import mlflow
from mlflow.tracking import MlflowClient

from adapters.interfaces import IModelRegistryAdapter


# TODO: expose via orchestration-api for the `orchestration:register-model`
# Custom Scaffolder Action (Golden Path #1) to call.
class MlflowAdapter(IModelRegistryAdapter):
    def __init__(self, tracking_uri: str | None = None):
        self.tracking_uri = tracking_uri or os.getenv(
            "MLFLOW_TRACKING_URI", "http://localhost:5000"
        )
        mlflow.set_tracking_uri(self.tracking_uri)
        self.client = MlflowClient(tracking_uri=self.tracking_uri)

    def register_model(
        self, name: str, artifact_uri: str, dataset_version: str | None = None
    ) -> dict:
        # No `version` param — MLflow assigns it, auto-incrementing per name.
        result = mlflow.register_model(model_uri=artifact_uri, name=name)
        if dataset_version is not None:
            # Caller already resolved the DVC hash; see data/README.md.
            self.client.set_model_version_tag(
                name, result.version, "dataset_version", dataset_version
            )
        return {"name": result.name, "version": result.version}

    def list_models(self, project: str | None = None) -> list[dict]:
        return [{"name": m.name} for m in self.client.search_registered_models()]

    def get_model_metrics(self, name: str, version: str) -> dict:
        mv = self.client.get_model_version(name=name, version=version)
        if mv.run_id is None:
            raise ValueError(f"Model version {name}:{version} has no associated run_id")
        run = self.client.get_run(mv.run_id)
        return dict(run.data.metrics)

    def get_dataset_lineage(self, name: str, version: str) -> list[dict]:
        # Reads lineage logged at training time (mlflow.log_input), not a
        # tag set here — a run can log more than one dataset.
        mv = self.client.get_model_version(name=name, version=version)
        if mv.run_id is None:
            raise ValueError(f"Model version {name}:{version} has no associated run_id")
        run = self.client.get_run(mv.run_id)
        return [
            {"name": d.dataset.name, "digest": d.dataset.digest, "source": str(d.dataset.source)}
            for d in run.inputs.dataset_inputs
        ]

    def set_model_version_tag(self, name: str, version: str, key: str, value: str) -> None:
        self.client.set_model_version_tag(name, version, key, value)

    def get_model_version_details(self, name: str, version: str) -> dict:
        mv = self.client.get_model_version(name=name, version=version)
        if mv.run_id is None:
            raise ValueError(f"Model version {name}:{version} has no associated run_id")
        run = self.client.get_run(mv.run_id)
        return {
            "version": mv.version,
            "run_id": mv.run_id,
            "tags": dict(mv.tags),
            "metrics": dict(run.data.metrics),
            "status": mv.status,
        }

    def get_latest_version(self, name: str) -> str:
        # Convenience method, not part of IModelRegistryAdapter — same
        # precedent as QdrantAdapter.ensure_collection() in vector_db_adapter.py.
        versions = self.client.search_model_versions(f"name='{name}'")
        if not versions:
            raise ValueError(f"Model {name} has no registered versions")
        return max(versions, key=lambda mv: int(mv.version)).version
