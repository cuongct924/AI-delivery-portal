# inference-services

Rendered `InferenceService` manifests, one per `<model>/<version>.yaml` —
written by Golden Path #2's `publish-catalog-pr` step (well, `publish-pr`,
see `examples/templates/register-deploy/template.yaml`) via
`services/orchestration-api/templates/inference_service.yaml.j2`. Nothing
in this directory is meant to be hand-edited; each file's lifecycle is
entirely PR-driven.

`infra/argocd/inference-services-app.yaml` watches this exact path — once
a PR here is merged to `main`, ArgoCD applies it to the cluster
automatically (see `infra/argocd/README.md`). Deleting a file (e.g. a
model version rollback) removes the corresponding `InferenceService` too
(`prune: true`).
