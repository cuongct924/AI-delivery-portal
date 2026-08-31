# kargo

Promotion + approval gate for `infra/environments/dev → staging → prod`
— the piece ConfigHub would have owned ("approval bound to a revision"),
here done by [Kargo](https://kargo.io) (Apache 2.0,
[`akuity/kargo`](https://github.com/akuity/kargo) — license verified by
reading the repo's `LICENSE` file directly), built by the same team as
ArgoCD (Akuity), explicitly designed to complement ArgoCD rather than
replace it. **Unlike Kubara, Kargo is not zero-footprint** — it runs a real
controller in the cluster (CRDs `Project`/`Warehouse`/`Stage`/`Freight`/
`Promotion` + a controller pod + its own UI), i.e. it is a new moving part,
not just a CLI.

## How it works here

Tenant-scoped end to end — `mlops-team` and `llmops-team` each get their
own `Warehouse` + `staging`/`prod` `Stage` pair, matching the tenant split
in `infra/argocd/` (`appproject-<env>-<tenant>.yaml`). One tenant's
promotion never touches the other's `Freight`/approval.

1. **`warehouse-inference-services-{mlops-team,llmops-team}.yaml`** watch
   `infra/environments/dev/inference-services/<tenant>/` on `main` —
   every commit a Golden Path merges there becomes a new `Freight` for
   that tenant.
2. **`stage-staging-{mlops-team,llmops-team}.yaml`** subscribe to their
   own `Freight` directly and **auto-promote** (per `project.yaml`'s
   `ProjectConfig.promotionPolicies`, which lists `staging-mlops-team` and
   `staging-llmops-team`) — copies the manifest into
   `infra/environments/staging/inference-services/<tenant>/` and pushes to
   `main`, which ArgoCD's
   `applicationset-inference-services-staging.yaml` then syncs.
3. **`stage-prod-{mlops-team,llmops-team}.yaml`** subscribe to their own
   `staging-<tenant>` Stage — **no** matching `promotionPolicies` entry
   for either, so both require manual approval (`kargo approve`/Kargo's
   own UI) per tenant, independently, before the same copy+push happens
   into `infra/environments/prod/inference-services/<tenant>/`.

The shared `promotiontask-copy-inference-services.yaml` PromotionTask
takes `tenant`/`envName` as explicit `vars` (passed at each Stage's
`task:` call site) rather than parsing them out of the Stage name.

Backstage never triggers steps 2-3 — no "promote-deploy" Golden Path
template exists. Promotion is entirely Kargo's job, matching
`CLAUDE.md`'s "business logic never lives in Backstage."

## Trạng thái xác minh — đọc trước khi chạy thật

`kargo` CLI **chưa cài trên máy** (`which kargo` → not found) lúc viết các
file này. Field-level schema của `Project`/`ProjectConfig`/`Warehouse`
`git` subscription/`Stage` được xác nhận bằng cách fetch trực tiếp
docs.kargo.io (không suy đoán) — **trừ 2 chỗ đã ghi rõ trong comment của
từng file**:
- `warehouse-inference-services-{mlops-team,llmops-team}.yaml`: nesting
  chính xác của `git:` subscription (repoURL/branch/includePaths) — tên
  field đúng, nesting là suy luận hợp lý, chưa thấy ví dụ đầy đủ.
- `promotiontask-copy-inference-services.yaml`: step `copy` xác nhận có
  tồn tại, nhưng field `inPath`/`outPath` chưa xác nhận được từ ví dụ thật.

**Trước khi dùng thật:** cài Kargo
([github.com/akuity/kargo](https://github.com/akuity/kargo) — quickstart
tại docs.kargo.io/quickstart/), `kubectl apply -f infra/kargo/`, rồi thử
`kargo promote` thủ công 1 lần cho `staging` trước khi tin tưởng
auto-promotion — sửa lại 2 chỗ trên nếu apply báo lỗi field không đúng.

## Điểm chưa xác nhận khác

Ai được bấm "approve" trên UI/CLI của Kargo — chưa xác nhận Kargo có tích
hợp OIDC thẳng vào Keycloak realm hiện có
(`infra/keycloak/realm-export.json`) hay cần cấu hình auth riêng. Cần đọc
docs.kargo.io phần auth/RBAC lúc cài đặt thật, không suy đoán trước.
