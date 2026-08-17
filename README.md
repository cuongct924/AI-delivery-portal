# AI Delivery Portal — Labs

Repo khởi động cho đề tài **AI Delivery Portal** (Viettel Digital Talent 2026 — Track Cloud).

Repo này KHÔNG chứa app Backstage đã build sẵn (vì Backstage cần chạy `create-app`
tương tác trên máy bạn với Node.js/Yarn thật). Thay vào đó, nó chứa:

- Hướng dẫn setup ngày 1 (`docs/day1-checklist.md`)
- Example config sẵn sàng copy vào app Backstage sau khi tạo (`examples/`)
- Khung thư mục cho phần backend Adapter (Python) sẽ code ở tuần 2-5 (`adapters/`)
- Ghi chú kiến trúc/roadmap tổng thể (`docs/architecture.md`)

## Cấu trúc thư mục

```
AI-delivery-portal/
├── README.md                          ← file này
├── docs/
│   ├── day1-checklist.md              ← checklist làm ngày mai, từng bước
│   ├── architecture.md                ← sơ đồ kiến trúc tổng thể (nhắc lại để tham chiếu)
│   └── roadmap.md                     ← lộ trình 12 tuần, đánh dấu tiến độ
├── examples/
│   ├── templates/hello-golden-path/
│   │   └── template.yaml              ← Software Template thử nghiệm đầu tiên
│   ├── catalog/
│   │   └── model-entity.yaml          ← ví dụ entity "model" trong Catalog
│   └── app-config.local.yaml.snippet  ← đoạn config cần thêm vào app-config.local.yaml
├── adapters/                          ← (rỗng, sẽ code tuần 2-5)
│   └── README.md                      ← giải thích kiến trúc Adapter Pattern sẽ code ở đây
├── plugins-workspace/                 ← nơi để symlink/copy các custom plugin sau này
│   └── README.md
└── scripts/
    ├── setup-backstage.sh             ← script chạy create-app + gợi ý bước tiếp theo
    └── setup-mlflow.sh                ← script dựng MLflow bằng Docker
```

## Cách dùng (ngày 1)

```bash
git clone <repo-này>   # hoặc giải nén nếu tải file zip
cd ai-delivery-portal-labs
cat docs/day1-checklist.md      # đọc checklist trước
bash scripts/setup-backstage.sh # tạo app Backstage thật (chạy ngoài repo này, sinh ra thư mục riêng)
bash scripts/setup-mlflow.sh    # dựng MLflow qua Docker
```

Sau khi `setup-backstage.sh` chạy xong, bạn sẽ có 1 thư mục app Backstage riêng
(ví dụ `ai-delivery-portal-app/`) nằm CẠNH repo lab này. Đây chính là hạt giống
để sau này đổi tên/merge thành repo chính thức `ai-delivery-portal`.

## Lộ trình mở rộng thành repo chính thức

```
Giai đoạn hiện tại (labs)          Giai đoạn sau (ai-delivery-portal)
──────────────────────────         ────────────────────────────────────
examples/templates/         →      packages/app-backstage/examples/templates/
adapters/ (rỗng)             →      services/orchestration-api/adapters/
docs/                        →      docs/ (giữ nguyên, cập nhật dần)
scripts/                     →      infra/scripts/
                              +      services/orchestration-api/  (FastAPI, tuần 4+)
                              +      infra/helm-charts/            (tuần 8+)
                              +      infra/argocd/                 (tuần 8+)
                              +      infra/opa-policies/            (tuần 8+)
```

Không cần tạo trước các thư mục ở cột phải — chỉ tạo khi thật sự bắt đầu code phần đó
(tránh thư mục rỗng vô nghĩa gây rối repo).

## Tham chiếu

Toàn bộ quyết định thiết kế (golden path, tech stack, benchmark, câu hỏi hỏi mentor...)
được tổng hợp trong sổ tay riêng — nên đặt cạnh repo này để tham chiếu song song:
`playbook-ai-delivery-portal.md`
