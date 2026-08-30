# argocd

3 ArgoCD `Application` CRs (`kubectl apply -f` per file — no
`ApplicationSet`/app-of-apps needed for just 3, would be premature
abstraction), installed by `scripts/setup-kserve-argocd-local.sh`:

- **`inference-services-app.yaml`** — watches `infra/inference-services/`
  (a `directory` source, no Helm — the files are already flat, fully-
  rendered `InferenceService` YAML). Closes Golden Path #2's known gap:
  merging its PR now actually deploys the model, instead of doing nothing.
- **`orchestration-api-app.yaml`** / **`portal-app.yaml`** — `source.helm`
  pointing at `infra/helm-charts/orchestration-api` /
  `infra/helm-charts/portal`. Additive to `docker compose up -d`/`yarn
  start`, not a replacement — this is the GitOps/production-like
  verification path, local dev keeps using docker-compose for its fast
  code-then-see-it loop.

All 3 use `syncPolicy.automated` with `prune: true` + `selfHeal: true` —
git is the single source of truth; a file deleted from the repo removes
the matching resource, and a manual `kubectl edit` on the cluster gets
reverted back to git.

**Deliberately not covered**: the 3 MCP servers (`mlops-server`/
`k8s-server`/`metrics-server`) — they're stdio-transport tools spawned
on-demand (`docker compose run -i ...`, `profiles: ["manual"]` in
`docker-compose.yml`), not long-running services. Deploying them as a
`Deployment` would crash-loop (no stdin attached). No Helm chart, no
ArgoCD Application for them.

Local setup: `bash scripts/setup-kserve-argocd-local.sh` (run
`scripts/setup-k8s-local.sh` first — same `kind` cluster). Get the admin
password: `kubectl -n argocd get secret argocd-initial-admin-secret -o
jsonpath='{.data.password}' | base64 -d`.
