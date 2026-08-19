# adapters

Python adapters following the Adapter Pattern — every adapter implements one
of the shared contracts in `interfaces.py`, so that `agents/` and
`services/orchestration-api/` can switch from Mock/MLflow/KServe to Viettel's
real system just by adding one new class.

```
adapters/
├── interfaces.py          # IModelRegistryAdapter, IInferenceAdapter, IWorkflowAdapter,
│                           # IVectorStoreAdapter, ILLMGatewayAdapter
├── mlflow_adapter.py       # IModelRegistryAdapter — MLflow SDK, connects to the mlflow service in docker-compose.yml
├── kserve_adapter.py       # IInferenceAdapter — deploy/query InferenceService on K8s
├── argo_adapter.py         # IWorkflowAdapter — trigger/track Argo Workflows (Golden Path #1)
├── vector_db_adapter.py    # IVectorStoreAdapter — Qdrant, powers RAG
├── llm_gateway_adapter.py  # ILLMGatewayAdapter — LiteLLM Proxy (rate limit/API key)
└── viettel_adapter.py      # IModelRegistryAdapter — stub raising NotImplementedError, pending mentor input (playbook section 10)
```

- `mlflow_adapter.py` reads `MLFLOW_TRACKING_URI` (defaults to `http://localhost:5000`).
- `kserve_adapter.py` needs a real kubeconfig — only usable from the infrastructure phase (week 8+).
- `argo_adapter.py` reads `ARGO_SERVER_URL` (defaults to `http://localhost:2746`), calls
  the WorkflowTemplate in `infra/argo-workflows/`.
- `vector_db_adapter.py` reads `QDRANT_URL` (defaults to `http://localhost:6333`), spun up
  via `docker compose up` — see `infra/vector-dbs/`.
- `llm_gateway_adapter.py` reads `LITELLM_GATEWAY_URL`/`LITELLM_MASTER_KEY`, spun up
  via `docker compose up` — see `infra/llm-gateways/`.

Install shared dependencies: `pip install -r adapters/requirements.txt`.
