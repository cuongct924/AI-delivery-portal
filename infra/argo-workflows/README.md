# argo-workflows

1 `WorkflowTemplate` for Golden Path #1 (Train → Track → Register),
triggered by `adapters/argo_adapter.py` via the Argo Server REST API:

- `train-register-template.yaml` (`train-register-golden-path`) — a
  `mode` parameter (`train` default, `finetune`) picks between training
  from scratch and fine-tuning `base-model-uri`, both on the same DAG.

`train-step` runs `training-image/` (built from `Dockerfile` in that
directory — dependencies installed at image build time, not pip-installed
per job run, which used to hit a real Docker Desktop I/O error mid-download).
It reads `TASK_TYPE`/`ALGORITHM`/`TARGET_COLUMN`/`ID_COLUMNS`/`TIME_COLUMN`
env vars, trains via `algorithm_registry.py` (~18 sklearn/XGBoost/LightGBM/
CatBoost algorithms), logs metrics + dataset lineage + the model to MLflow,
then hands the resulting `runs:/...` artifact URI and dataset digest to
`register-step`, which calls `POST /models/register` on orchestration-api
(business logic — the actual MLflow registration — stays there, not in the
workflow pod, per CLAUDE.md). The local `kind` + Argo Workflows infra to
actually run this is set up below.

Local testing — run from the repo root:

```bash
bash scripts/setup-k8s-local.sh
```

This creates a `kind` cluster (`infra/k8s-local-cluster/kind-config.yaml`),
installs Argo Workflows, provisions the `train-register-workflow`
ServiceAccount/RBAC, builds `training-image/` and loads it into the cluster
(`kind load docker-image` — no registry needed for local dev), and applies
the WorkflowTemplate. Re-run it after any change under `training-image/` to
rebuild + reload the image. See the script for the full breakdown and
next-step instructions it prints (`docker compose up -d`, `dvc pull`,
`yarn start`).

**Reaching host-machine services from a workflow step container:** use
`http://host.docker.internal:5000` (mlflow) and
`http://host.docker.internal:8000` (orchestration-api), not `localhost` —
step containers run as pods on the kind node, which is itself a Docker
container. This resolves correctly under Docker Desktop for Mac (the repo
owner's OS is Darwin/macOS); other Docker setups (e.g. Docker Desktop for
Linux, `colima`) may need a different host address.
