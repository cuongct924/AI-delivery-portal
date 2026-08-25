# argo-workflows

2 `WorkflowTemplate`s for Golden Path #1 (Train → Track → Register), both
triggered by `adapters/argo_adapter.py` via the Argo Server REST API:

- `train-register-template.yaml` (`train-register-golden-path`) — train from scratch.
- `fine-tune-template.yaml` (`fine-tune-golden-path`) — fine-tune from an
  existing model, takes an extra `base-model-uri` parameter.

Each `train-step`/`fine-tune-step` container trains (or fine-tunes) a
`scikit-learn` `LogisticRegression` on `data/fraud-detection-sample.csv`,
logs metrics + dataset lineage + the model to MLflow, then hands the
resulting `runs:/...` artifact URI and dataset digest to `register-step`,
which calls `POST /models/register` on orchestration-api (business logic —
the actual MLflow registration — stays there, not in the workflow pod, per
CLAUDE.md). The local `kind` + Argo Workflows infra to actually run them is
set up below.

Local testing — run from the repo root:

```bash
bash scripts/setup-k8s-local.sh
```

This creates a `kind` cluster (`infra/k8s-local-cluster/kind-config.yaml`),
installs Argo Workflows, provisions the `train-register-workflow`
ServiceAccount/RBAC these templates reference, and applies both. See that
script for the full breakdown and next-step instructions it prints
(`docker compose up -d`, `dvc pull`, `yarn start`).

**Reaching host-machine services from a workflow step container:** use
`http://host.docker.internal:5000` (mlflow) and
`http://host.docker.internal:8000` (orchestration-api), not `localhost` —
step containers run as pods on the kind node, which is itself a Docker
container. This resolves correctly under Docker Desktop for Mac (the repo
owner's OS is Darwin/macOS); other Docker setups (e.g. Docker Desktop for
Linux, `colima`) may need a different host address.
