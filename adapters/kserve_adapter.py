"""Adapter for KServe — deploys/queries models as InferenceService on K8s.

Uses the Kubernetes Python client to operate on the `InferenceService`
custom resource (serving.kserve.io/v1beta1). Requires a kubeconfig pointing
at a real cluster.
"""

from typing import cast

from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

from adapters.interfaces import IInferenceAdapter

GROUP = "serving.kserve.io"
VERSION = "v1beta1"
PLURAL = "inferenceservices"


class KServeAdapter(IInferenceAdapter):
    def __init__(self, namespace: str = "default"):
        config.load_kube_config()
        self.namespace = namespace
        self.api = client.CustomObjectsApi()

    def deploy_model(
        self, name: str, version: str, model_uri: str, traffic_fields: dict | None = None
    ) -> dict:
        """Creates the InferenceService, or patches it if a version was
        already deployed under this name (patch first — the common case
        for adapters/deploy_strategies.py's TrafficSplitStrategy, which by
        definition requires a prior deploy to exist)."""
        body = {
            "apiVersion": f"{GROUP}/{VERSION}",
            "kind": "InferenceService",
            "metadata": {"name": name, "labels": {"version": version}},
            "spec": {
                "predictor": {
                    **(traffic_fields or {}),
                    "model": {
                        "modelFormat": {"name": "mlflow"},
                        "storageUri": model_uri,
                    },
                }
            },
        }
        try:
            result = self.api.patch_namespaced_custom_object(
                GROUP, VERSION, self.namespace, PLURAL, name, body
            )
        except ApiException as exc:
            if exc.status != 404:
                raise
            result = self.api.create_namespaced_custom_object(
                GROUP, VERSION, self.namespace, PLURAL, body
            )
        # cast: only non-dict when async_req=True, which we never pass.
        return cast(dict, result)

    def get_inference_status(self, name: str) -> dict:
        return cast(
            dict,
            self.api.get_namespaced_custom_object_status(
                GROUP, VERSION, self.namespace, PLURAL, name
            ),
        )

    def predict(self, name: str, payload: dict) -> dict:
        raise NotImplementedError(
            "Call the InferenceService's HTTP endpoint directly "
            "(get the URL from get_inference_status) instead of going through this adapter"
        )
