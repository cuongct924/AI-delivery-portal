"""Adapter for KServe — deploys/queries models as InferenceService on K8s.

Uses the Kubernetes Python client to operate on the `InferenceService`
custom resource (serving.kserve.io/v1beta1). Requires a kubeconfig pointing
at a real cluster — only usable starting from the infrastructure phase
(see docs/roadmap.md, week 8+).
"""

from typing import cast

from kubernetes import client, config

from adapters.interfaces import IInferenceAdapter

GROUP = "serving.kserve.io"
VERSION = "v1beta1"
PLURAL = "inferenceservices"


# TODO: expose via orchestration-api for the `orchestration:deploy-model`
# Custom Scaffolder Action (Golden Path #2) — decide direct-call vs GitOps-commit first.
class KServeAdapter(IInferenceAdapter):
    def __init__(self, namespace: str = "default"):
        config.load_kube_config()
        self.namespace = namespace
        self.api = client.CustomObjectsApi()

    def deploy_model(self, name: str, version: str, model_uri: str) -> dict:
        body = {
            "apiVersion": f"{GROUP}/{VERSION}",
            "kind": "InferenceService",
            "metadata": {"name": name, "labels": {"version": version}},
            "spec": {
                "predictor": {
                    "model": {
                        "modelFormat": {"name": "mlflow"},
                        "storageUri": model_uri,
                    }
                }
            },
        }
        # cast: only non-dict when async_req=True, which we never pass.
        return cast(
            dict,
            self.api.create_namespaced_custom_object(GROUP, VERSION, self.namespace, PLURAL, body),
        )

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
