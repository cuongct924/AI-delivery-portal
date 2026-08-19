# llm-gateways

LLM Gateway (LiteLLM Proxy) — routes requests and manages API keys & rate
limits when calling multiple different LLMs, instead of `orchestration-api`
calling each vendor's SDK directly. **Works right away, locally** via
`docker compose up` (`litellm` service, OpenAI-compatible API at
`http://localhost:4000`).

`adapters/llm_gateway_adapter.py` (`LiteLLMGatewayAdapter`) implements
`ILLMGatewayAdapter` — calls `chat_completion()` through the gateway instead
of calling the Anthropic SDK directly, for centralized rate-limit/API-key
management.

`litellm-config.yaml` is a sample config — replace `api_key` with a real
environment variable before running (do not commit real keys).
