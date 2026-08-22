"""Only implement this after the mentor confirms Viettel's real API (see playbook item 10)."""

from adapters.interfaces import IModelRegistryAdapter


class ViettelAdapter(IModelRegistryAdapter):
    def register_model(
        self,
        name: str,
        version: str,
        artifact_uri: str,
        dataset_version: str | None = None,
    ) -> dict:
        raise NotImplementedError("Waiting for Viettel's real API details")

    def list_models(self, project: str | None = None) -> list[dict]:
        raise NotImplementedError("Waiting for Viettel's real API details")

    def get_model_metrics(self, name: str, version: str) -> dict:
        raise NotImplementedError("Waiting for Viettel's real API details")
