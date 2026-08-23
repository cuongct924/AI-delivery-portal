# adapters

Python adapters following the Adapter Pattern — every adapter implements one
of the shared contracts in `interfaces.py`, so that `agents/` and
`services/orchestration-api/` can switch from Mock to a real self-hosted
backend just by adding one new class.

```
adapters/
├── interfaces.py          # IModelRegistryAdapter, IInferenceAdapter, IWorkflowAdapter,
│                           # IVectorStoreAdapter, ILLMGatewayAdapter, IFeatureStoreAdapter
├── mlflow_adapter.py       # IModelRegistryAdapter — MLflow SDK, connects to the mlflow service in docker-compose.yml
├── kserve_adapter.py       # IInferenceAdapter — deploy/query InferenceService on K8s
├── argo_adapter.py         # IWorkflowAdapter — trigger/track Argo Workflows (Golden Path #1)
├── vector_db_adapter.py    # IVectorStoreAdapter — Qdrant, powers RAG
├── llm_gateway_adapter.py  # ILLMGatewayAdapter — LiteLLM Proxy (rate limit/API key)
└── feature_store_adapter.py # IFeatureStoreAdapter — Feast, offline/online feature retrieval
```

- `mlflow_adapter.py` reads `MLFLOW_TRACKING_URI` (defaults to `http://localhost:5000`).
  `register_model()` accepts an optional `dataset_version` (the DVC md5 hash from
  the dataset's `.dvc` file, see `../data/`) and stores it as a model version tag
  — the caller resolves the hash, this adapter just passes it through.
- `kserve_adapter.py` needs a real kubeconfig — only usable from the infrastructure phase (week 8+).
- `argo_adapter.py` reads `ARGO_SERVER_URL` (defaults to `http://localhost:2746`), calls
  the WorkflowTemplate in `infra/argo-workflows/`.
- `vector_db_adapter.py` reads `QDRANT_URL` (defaults to `http://localhost:6333`), spun up
  via `docker compose up` — see `infra/vector-dbs/`.
- `llm_gateway_adapter.py` reads `LITELLM_GATEWAY_URL`/`LITELLM_MASTER_KEY`, spun up
  via `docker compose up` — see `infra/llm-gateways/`.
- `feature_store_adapter.py` reads `FEAST_REPO_PATH` (defaults to `infra/feature-store`) —
  needs that Feast repo (feature_store.yaml + entity/feature definitions) provisioned
  before it can connect for real, same infra-phase caveat as `kserve_adapter.py`.

Install shared dependencies: `pip install -r adapters/requirements.txt`.\
