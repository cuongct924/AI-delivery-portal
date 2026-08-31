# kubara

Declares, in one place, which environments exist and which
`orchestration-api`/`portal`/`inference-services` capability runs in each
— replaces hand-writing 3 near-duplicate ArgoCD `Application`s per
environment. Kubara ([`kubara-io/kubara`](https://github.com/kubara-io/kubara),
Apache 2.0) is a standalone CLI — **no controller/runtime is installed in
the cluster**, it only reads `config.yaml`, resolves it against a catalog,
and writes Helm/manifest output + ArgoCD `ApplicationSet`/`AppProject`
wiring into Git. Not added to `docker-compose.yml` — it's a CLI invoked
locally or in CI, the same way `helm template`/`kustomize build` already
are.

## Trạng thái xác minh (quan trọng — đọc trước khi tin `config.yaml`)

`kubara` **chưa được cài trên máy** lúc viết plan này (`which kubara` →
not found). `config.yaml` trong thư mục này là **bản nháp**, viết dựa trên
mô tả ở docs.kubara.io (`config.yaml` "defines your cluster profile and
the services Argo CD will manage") — không phải output thật của
`kubara init --local`, vì trang docs không lộ chi tiết field-level schema
qua fetch trong phiên nghiên cứu này.

**Trước khi dùng thật:**
1. Cài `kubara` ([github.com/kubara-io/kubara](https://github.com/kubara-io/kubara) — xem hướng dẫn cài trong repo đó).
2. Chạy `kubara init --prep --local` rồi `kubara init --local` trong thư mục này, so khớp `config.yaml` thật với bản nháp — sửa lại field nào lệch.
3. Chạy `kubara bootstrap --local ai-delivery-portal` để tạo `infra/environments/` + `infra/argocd/applicationset-*.yaml`/`appproject-*.yaml` thật.
4. Nếu catalog của Kubara không có sẵn component tự build như
   `orchestration-api`/`portal` (Kubara mạnh nhất ở catalog có sẵn kiểu
   cert-manager/ingress) — rút về dùng bản viết tay đã có sẵn trong
   `infra/argocd/` (không mất công, output tương đương).

## Vì sao không dùng ConfigHub cùng với Kubara

Xem `docs/llmops-lifecycle-plan.md`/lịch sử trao đổi — Kubara mã nguồn mở
thật (Apache 2.0), không phụ thuộc ConfigHub. ConfigHub (SaaS/self-hosted
enterprise trả phí của ConfigHub Inc, không phải cùng dự án với
`ConfigHubPub/ConfigHubPlatform` trên GitHub) không được dùng — vendor
lock-in, và không có bản mã nguồn mở thật sự tương đương. Phần "promotion/
approval" mà ConfigHub lẽ ra đảm nhiệm được thay bằng Kargo — xem
`infra/kargo/README.md`.
