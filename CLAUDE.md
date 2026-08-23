# AI Delivery Portal

Portal (Backstage) + Orchestration API (FastAPI) + AI Agent/MCP + Adapter layer
+ GitOps infra, one repo. See `docs/architecture.md` for the component diagram
and `docs/playbook-ai-delivery-portal.md` for design decisions/rationale.

## Commands

TypeScript (root, Yarn workspaces `packages/*`, `plugins/*`):
```bash
yarn start        # run the Portal (Backstage dev server)
yarn tsc           # type check
yarn lint:all      # lint
yarn new           # scaffold a new plugin/package
```

Python (each service under `adapters/`, `services/orchestration-api/`,
`agents/mcp-servers/*` has its own `requirements.txt` — see Makefile
`SERVICE_REQS`):
```bash
make install   # create .venv, install dev.lock.txt + pre-commit hook
make lock       # regenerate all *.lock.txt — run after editing any requirements.txt
make check      # lint + format-check + typecheck + test (what CI runs)
make run-orchestration-api / run-mlops-mcp / run-k8s-mcp / run-metrics-mcp
```

Local infra:
```bash
docker compose up -d   # mlflow, keycloak, prometheus, grafana, qdrant, litellm, orchestration-api, 3 MCP servers
bash scripts/run-mcp-local.sh mlops|k8s|metrics   # run one MCP server without Docker
```

Run `make check` and `yarn tsc && yarn lint:all` before committing — CI
(`.github/workflows/ci.yml`) runs the exact same commands, nothing else.

## Coding standards

- Python: see `.claude/rules/python-standards.md` (ruff + pyright + pytest,
  Google-style docstrings, class layout order). Applies to `adapters/`,
  `agents/`, `services/orchestration-api/`.
- TypeScript/React: `packages/app-backstage`, `plugins/*` are React — use the
  `typescript-typing-expert` skill. `packages/backend` is plain Node.js
  (Backstage backend system) — **no React there**.
- Every Adapter implements a shared interface from `adapters/interfaces.py`
  (Adapter Pattern) — switching Mock → real backend (MLflow/KServe/Argo/...)
  means adding one new class, never touching callers.
- **Business logic never lives in Backstage.** A Custom Scaffolder Action in
  `template.yaml` only makes an HTTP call to `services/orchestration-api`;
  the FastAPI service owns Adapter/Factory/policy logic.

## Architecture (directories)

```
packages/            Portal (Backstage) — app-backstage (React/TS UI) + backend (Node, no React)
plugins/              Backstage plugins — prompt-registry (Prompt version UI)
services/             orchestration-api — FastAPI BFF, MCP client, auth, evaluations
agents/               AI Agent & MCP — mcp-servers/, skills/, prompts/
adapters/             Adapter Pattern — MLflow, KServe, Argo, Qdrant, LiteLLM
infra/                GitOps infra — monitoring/vector-dbs/llm-gateways (active); helm-charts/argocd/opa-policies (week 8+)
examples/             sample Catalog entity + Software Template (wired into app-config.yaml)
docs/                 architecture, roadmap, playbook
```

## Workflow

- Repo is hosted on **GitHub**; CI runs via `.github/workflows/ci.yml`.
- Adding a new Python service: add its `requirements.txt` path to `Makefile`'s
  `SERVICE_REQS`, run `make lock`, add it to `docker-compose.yml`, and add a
  build+scan block to `ci.yml`.
- Adding a Catalog entity/template: add it to `app-config.yaml`
  `catalog.locations` **and** to `app-config.production.yaml` (different
  relative path — `../../examples/...` vs `./examples/...`, not synced
  automatically).
- No `fail_under` coverage gate yet (`pyproject.toml`) — most adapters are
  still stubs by design (`docs/roadmap.md`); don't chase coverage % before the
  real logic behind it exists.
