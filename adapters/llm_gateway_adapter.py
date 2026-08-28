"""Adapter for the LLM Gateway (LiteLLM Proxy) — routes requests and manages
API keys & rate limits when calling multiple different LLMs, instead of
calling each vendor's SDK directly. Spun up via docker-compose.yml (the
`litellm` service), config at infra/llm-gateways/litellm-config.yaml.
"""

import os

import httpx

from adapters.interfaces import ILLMGatewayAdapter


class LiteLLMGatewayAdapter(ILLMGatewayAdapter):
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        self.base_url = base_url or os.getenv("LITELLM_GATEWAY_URL", "http://localhost:4000")
        self.api_key = api_key or os.getenv("LITELLM_MASTER_KEY", "")

    def chat_completion(self, model: str, messages: list[dict], **kwargs) -> dict:
        response = httpx.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": model, "messages": messages, **kwargs},
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def list_models(self) -> list[dict]:
        response = httpx.get(
            f"{self.base_url}/models",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=10,
        )
        response.raise_for_status()
        return response.json().get("data", [])

    def embed(self, model: str, input_texts: list[str]) -> list[list[float]]:
        response = httpx.post(
            f"{self.base_url}/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": model, "input": input_texts},
            timeout=30,
        )
        response.raise_for_status()
        return [item["embedding"] for item in response.json()["data"]]
