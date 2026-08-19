# argo-workflows

`WorkflowTemplate` for Golden Path #1 (Train → Track → Register), triggered by
`adapters/argo_adapter.py` via the Argo Server REST API. **The manifest here
is a skeleton illustrating the DAG structure** — the real `train-step`/
`register-step` logic will be written at week 8+ once a real K8s cluster
exists (see `docs/roadmap.md`).

Local testing (requires the Argo CLI + a cluster/minikube, outside the scope
of Mac-local day-1):

```bash
argo submit --watch train-register-template.yaml
```
