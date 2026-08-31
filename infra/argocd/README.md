# argocd

Multi-tenancy = **[môi trường] × [tenant]**, theo đúng công thức chuẩn của
ArgoCD multi-tenancy (mentor xác nhận lại pattern này ở lượt trao đổi thứ
2): mỗi cặp (môi trường, tenant) là 1 `AppProject` riêng, chỉ được sync vào
đúng 1 namespace của riêng nó — cô lập hoàn toàn giữa `mlops-team` và
`llmops-team`, kể cả khi cùng 1 môi trường.

Cài bằng `scripts/setup-kserve-argocd-local.sh` — thay cho setup 3
`Application` viết tay đơn-môi-trường ban đầu (xem lịch sử Git; giữ 3 file
viết tay lúc chỉ có 1 môi trường là hợp lý — tránh premature abstraction —
nhưng giờ có 3 môi trường × 2 tenant thì viết tay sẽ thành 6+ file gần
giống hệt nhau, đúng lúc nên generate hoá, xem `infra/kubara/README.md`,
nơi lẽ ra nên sinh ra các file này thay vì viết tay):

## AppProject — Bước 1: `[môi trường] + [tenant]`

- `appproject-{dev,staging,prod}-{mlops-team,llmops-team}.yaml` (6 file) —
  mỗi file chỉ cho phép sync vào đúng 1 namespace
  `ai-delivery-portal-<env>-<tenant>`. Đây là ranh giới RBAC multi-tenant
  thật, thực thi bởi chính ArgoCD.
- `appproject-platform.yaml` — riêng cho `orchestration-api`/`portal`
  (không phải tài nguyên multi-tenant, không tách theo tenant), cả 3 môi
  trường, chỉ `platform-team`.

## ApplicationSet — Bước 2, Cách 2: 1 ApplicationSet/môi trường, quét qua tenant

- `applicationset-inference-services-{dev,staging,prod}.yaml` (3 file) —
  mỗi file dùng `git` directory generator quét
  `infra/environments/<env>/inference-services/*` (tự nhận diện thư mục
  `mlops-team/`, `llmops-team/`), sinh 1 `Application`/tenant, gán đúng
  `AppProject` `<env>-<tenant>` tương ứng và namespace
  `ai-delivery-portal-<env>-<tenant>`. `dev` closes Golden Path's gap
  (merge PR = deploy); `staging`/`prod` populated only by that tenant's
  own Kargo `Warehouse`/`Stage` pair (`infra/kargo/`), never a manual sync.
- `applicationset-orchestration-api.yaml` / `applicationset-portal.yaml`
  — không tách theo tenant (không phải tài nguyên multi-tenant); dùng
  `list` generator (không phải `git` generator) vì cần gán `project`
  khác nhau có điều kiện mà generator dạng thư mục không biểu đạt được —
  cả 3 môi trường đều `project: platform`. `source.helm.valueFiles` trỏ
  overlay đúng môi trường trong `infra/environments/<env>/`.

Toàn bộ dùng `syncPolicy.automated` với `prune: true` + `selfHeal: true` —
git là nguồn sự thật duy nhất. `CreateNamespace=true` vì
`ai-delivery-portal-{dev,staging,prod}-{mlops-team,llmops-team}` đều là
namespace mới.

Cả 7 `AppProject`'s `roles`/`groups` block giả định ArgoCD tự có OIDC/SSO
nối vào Keycloak realm (`infra/keycloak/realm-export.json`) —
**chưa được cấu hình/verify trong repo này** — tới lúc đó RBAC chưa có
tác dụng thật.

**Chủ động không làm:** 3 MCP server (`mlops-observability-server`/
`golden-paths-server`) — stdio-transport, spawn theo yêu cầu, không phải
long-running service; deploy dạng `Deployment` sẽ crash-loop (không có
stdin). Không có Helm chart/ArgoCD Application cho chúng.

Lấy admin password: `kubectl -n argocd get secret
argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d`.
