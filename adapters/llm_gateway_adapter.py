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
        result = response.json()
        # Per-call cost — LiteLLM returns this as a response header, not in
        # the OpenAI-compatible JSON body, so it has to be read here or
        # callers (who only see the parsed JSON) can't get at it. None
        # when the model has no cost entry in litellm-config.yaml (e.g. a
        # self-hosted model from the Serving LLM Golden Path) — callers
        # must handle that, not assume a number.
        cost_header = response.headers.get("x-litellm-response-cost")
        result["response_cost_usd"] = float(cost_header) if cost_header is not None else None
        return result

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
