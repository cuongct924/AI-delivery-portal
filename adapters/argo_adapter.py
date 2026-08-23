"""Adapter for Argo Workflows — triggers and tracks workflows via the Argo Server REST API.

Used for Golden Path #1 (Train → Track → Register): triggers the WorkflowTemplate
defined in infra/argo-workflows/, and tracks status to report back via Portal/Agent.
"""

import os

import httpx

from adapters.interfaces import IWorkflowAdapter


# TODO: expose via orchestration-api for the `orchestration:trigger-training`
# Custom Scaffolder Action (Golden Path #1) to call.
class ArgoAdapter(IWorkflowAdapter):
    def __init__(self, base_url: str | None = None, namespace: str = "default"):
        self.base_url = base_url or os.getenv("ARGO_SERVER_URL", "http://localhost:2746")
        self.namespace = namespace

    def trigger_workflow(self, template_name: str, parameters: dict) -> dict:
        payload = {
            "resourceKind": "WorkflowTemplate",
            "resourceName": template_name,
            "submitOptions": {"parameters": [f"{k}={v}" for k, v in parameters.items()]},
        }
        response = httpx.post(
            f"{self.base_url}/api/v1/workflows/{self.namespace}/submit",
            json=payload,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()

    def get_workflow_status(self, workflow_name: str) -> dict:
        response = httpx.get(
            f"{self.base_url}/api/v1/workflows/{self.namespace}/{workflow_name}",
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        return {"name": workflow_name, "phase": data.get("status", {}).get("phase")}
