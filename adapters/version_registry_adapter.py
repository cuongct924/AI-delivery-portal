"""File-backed IVersionRegistryAdapter — no DB exists for
orchestration-api today; this fills that gap for LLMOps prompt/RAG-index
version tracking without inventing new infra.

Not MlflowAdapter.set_model_version_tag() reused instead — that's coupled
to the MLflow Model Registry's "model version" (created by
mlflow.register_model(artifact_uri=...), which must be MLflow-loadable). A
prompt or a RAG index pointer isn't a model artifact — see
docs/llmops-lifecycle-plan.md mục 8 Q2 for the full reasoning.
"""

import json
import os
import threading
from pathlib import Path

from adapters.interfaces import IVersionRegistryAdapter


class JsonFileVersionRegistryAdapter(IVersionRegistryAdapter):
    def __init__(self, path: str | None = None):
        self.path = Path(path or os.getenv("LLMOPS_REGISTRY_PATH", ".state/llmops-registry.json"))
        self._lock = threading.Lock()

    def register_version(self, kind: str, name: str, metadata: dict) -> str:
        with self._lock:
            data = self._read()
            entry = data.setdefault(kind, {}).setdefault(
                name, {"versions": {}, "active_version": None}
            )
            # Same string-of-an-incrementing-int shape MLflow uses for
            # model versions — cheap, no UUID needed for a single-writer
            # local file.
            version = str(len(entry["versions"]) + 1)
            entry["versions"][version] = metadata
            self._write(data)
            return version

    def list_names(self, kind: str) -> list[str]:
        with self._lock:
            data = self._read()
            return list(data.get(kind, {}))

    def get_version(self, kind: str, name: str, version: str) -> dict:
        with self._lock:
            data = self._read()
            try:
                return data[kind][name]["versions"][version]
            except KeyError as exc:
                raise ValueError(f"{kind}/{name} has no version {version!r}") from exc

    def list_versions(self, kind: str, name: str) -> dict[str, dict]:
        with self._lock:
            data = self._read()
            return data.get(kind, {}).get(name, {}).get("versions", {})

    def get_active_version(self, kind: str, name: str) -> str | None:
        with self._lock:
            data = self._read()
            return data.get(kind, {}).get(name, {}).get("active_version")

    def set_active_version(self, kind: str, name: str, version: str) -> None:
        with self._lock:
            data = self._read()
            try:
                entry = data[kind][name]
            except KeyError as exc:
                raise ValueError(f"{kind}/{name} has no registered versions") from exc
            if version not in entry["versions"]:
                raise ValueError(f"{kind}/{name} has no version {version!r}")
            entry["active_version"] = version
            self._write(data)

    def _read(self) -> dict:
        if not self.path.exists():
            return {}
        return json.loads(self.path.read_text())

    def _write(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2))
