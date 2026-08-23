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
        self,
        name: str,
        version: str,
        artifact_uri: str,
        dataset_version: str | None = None,
    ) -> dict:
        result = mlflow.register_model(model_uri=artifact_uri, name=name)
        if dataset_version is not None:
            # DVC md5 hash — just a fingerprint tag, no DVC pull needed.
            self.client.set_model_version_tag(
                name=result.name,
                version=result.version,
                key="dataset_version",
                value=dataset_version,
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
