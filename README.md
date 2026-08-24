# AI Delivery Portal

**A CI/CD Portal and Internal Developer Platform for MLOps/LLMOps**

Repository for the **AI Delivery Portal** project (Viettel Digital Talent 2026 — Cloud Track - Phase 02).

An MLOps platform built as an Internal Developer Platform (IDP) for AI/ML workloads:

- Acts as the **DevEx and orchestration layer** on top of the AI platform ecosystem — Model Registry, Model Experiments, AI Inference, AI Notebooks
- Provides **golden paths** so developers and ML engineers can ship standard MLOps/LLMOps workflows without hand-rolling infrastructure each time

Official structure: Portal (Backstage) + Orchestration API (FastAPI) + AI Agent/MCP
+ Adapter layer + GitOps infrastructure.

## Directory structure

```
AI-delivery-portal/
├── packages/            ← Portal (Backstage) — app-backstage (React/TS UI) + backend
├── plugins/              ← Backstage plugins — prompt-registry (Prompt version UI)
├── services/             ← orchestration-api — FastAPI BFF, MCP client, auth, evaluations
├── agents/               ← AI Agent & MCP — mcp-servers/, skills/, prompts/
├── adapters/             ← Adapter Pattern — MLflow, KServe, Argo, Qdrant, LiteLLM, Feast, JupyterHub
├── infra/                ← GitOps infra — monitoring/vector-dbs/llm-gateways (active); helm-charts/argocd/opa-policies (week 8+)
├── data/                 ← datasets versioned with DVC (S3-compatible remote, see data/README.md)
├── examples/             ← Catalog entity + 2 Golden Path templates (train-track-register, register-deploy)
├── scripts/              ← run-mcp-local.sh
├── docs/                 ← architecture, roadmap, playbook
├── app-config.yaml       ← shared Backstage config (catalog, scaffolder, auth, proxy...)
├── docker-compose.yml    ← full local stack (mlflow, keycloak, prometheus, grafana, qdrant, minio, litellm, orchestration-api, MCP servers)
└── README.md
```

See [`docs/architecture.md`](docs/architecture.md) for the full component breakdown and design rationale.

## Usage

```bash
yarn install && yarn start      # run the Backstage Portal (packages/app-backstage + packages/backend)
yarn tsc                        # type check the whole TS workspace
yarn lint                       # lint — only files changed vs origin/master (fast, day-to-day)
yarn lint:all                   # lint — whole repo (what CI runs)
yarn fix                        # auto-fix what's fixable
yarn workspace <name> add <pkg> # add a dependency to one workspace (packages/app-backstage, backend, plugins/prompt-registry...)
cp .env.example .env            # fill in ANTHROPIC_API_KEY before running orchestration-api/litellm
docker compose up               # run the whole stack: mlflow, keycloak, prometheus, grafana, qdrant, minio, litellm,
                                 # orchestration-api, mlops/k8s/metrics MCP servers
bash scripts/run-mcp-local.sh mlops   # or: run a single MCP server standalone, no Docker needed

make install    # create a Python 3.12 .venv, install ruff + pyright + pytest + every service's requirements.txt
make lint       # ruff check .
make format     # ruff format .
make typecheck  # pyright
make test       # pytest (tests/)
make check      # lint + typecheck + test
```

- Portal UI: `http://localhost:3000` & Backend: `http://localhost:7007`
- Catalog is preconfigured in [`app-config.yaml`](app-config.yaml) to read [`examples/catalog/model-entity.yaml`](examples/catalog/model-entity.yaml) and the [`train-track-register`](examples/templates/train-track-register/template.yaml) / [`register-deploy`](examples/templates/register-deploy/template.yaml) templates
- **Prompt Registry** (sidebar page, from [`plugins/prompt-registry/`](plugins/prompt-registry/)) reads data through the `/orchestration-api` proxy — [`orchestration-api`](services/orchestration-api/) must be running (`docker compose up` or local `uvicorn`) for data to appear

### Test CI locally

[`act`](https://github.com/nektos/act) runs [`.github/workflows/ci.yml`](.github/workflows/ci.yml) itself, on your machine, before you push:

```bash
# For MacOS only
brew install act
echo "--container-architecture linux/amd64" >> ~/.actrc   # Apple Silicon: match the amd64 GitHub-hosted runner

act -l                                                      # list jobs, sanity-check the workflow parses
act pull_request --container-architecture linux/amd64       # run the full pipeline (skips the GHCR push step — needs main branch)
act pull_request -j python-checks                           # run a single job: python-checks example
```

## Reference

All design decisions (golden path, tech stack, benchmarks, questions for the
mentor...) are compiled in a separate notebook — keep it alongside this repo
for reference:
[`docs/playbook-ai-delivery-portal.md`](docs/playbook-ai-delivery-portal.md)
