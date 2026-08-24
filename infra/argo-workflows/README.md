# argo-workflows

2 `WorkflowTemplate`s for Golden Path #1 (Train → Track → Register), both
triggered by `adapters/argo_adapter.py` via the Argo Server REST API:

- `train-register-template.yaml` (`train-register-golden-path`) — train from scratch.
- `fine-tune-template.yaml` (`fine-tune-golden-path`) — fine-tune from an
  existing model, takes an extra `base-model-uri` parameter.

**Both are skeletons illustrating the DAG structure** — the real
`train-step`/`fine-tune-step`/`register-step` logic will be written at
week 8+ once a real K8s cluster exists (see `docs/roadmap.md`).

Local testing (requires the Argo CLI + a cluster/minikube, outside the scope
of Mac-local day-1):

```bash
argo submit --watch train-register-template.yaml
argo submit --watch fine-tune-template.yaml
```
