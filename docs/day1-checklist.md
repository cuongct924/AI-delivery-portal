# Ngày 1 — Checklist Test-drive Backstage + MLflow

Mục tiêu ngày mai: **chỉ Backstage + MLflow**. KHÔNG đụng KServe/Kubeflow hôm nay
(đã tìm hiểu lý thuyết trước rồi, phần setup thật để dành riêng buổi khác — xem
`docs/roadmap.md`).

## Yêu cầu trước khi bắt đầu

- [ ] Node.js 20 hoặc 22 LTS đã cài (`node -v` để kiểm tra)
- [ ] Yarn đã cài (`yarn -v`) — Backstage dùng Yarn, không dùng npm để chạy app
- [ ] Docker đã cài và chạy được (`docker ps`)
- [ ] Git đã cấu hình (username/email)

## Sáng (2-3 giờ) — Dựng Backstage app

```bash
bash scripts/setup-backstage.sh
```

Script sẽ hỏi tên app — gợi ý đặt `ai-delivery-portal-app` để sau này dễ nhận diện
là "hạt giống" của repo chính thức.

- [ ] `yarn dev` chạy được, mở `localhost:3000` thấy UI Backstage
- [ ] Đi loanh quanh: sidebar, trang Catalog (đang trống), trang "Create..."
- [ ] Đọc lướt cấu trúc thư mục app vừa sinh ra: `packages/app` (frontend),
      `packages/backend` (backend) — ghi nhớ đây là 2 chỗ sẽ viết custom plugin sau

## Trưa–chiều sớm (1-2 giờ) — Đăng ký entity đầu tiên vào Catalog

- [ ] Copy `examples/catalog/model-entity.yaml` vào app vừa tạo
- [ ] Vào UI → Catalog → "Register Existing Component" → trỏ tới file (có thể
      cần push lên 1 GitHub repo/gist tạm để Backstage đọc được qua URL, hoặc
      dùng file provider nếu chạy local — xem ghi chú trong file example)
- [ ] Thấy entity `fraud-detection-model` xuất hiện trong danh sách Catalog

## Chiều (2-3 giờ) — Chạy thử Software Template đầu tiên

- [ ] Copy `examples/templates/hello-golden-path/template.yaml` vào app
- [ ] Đăng ký template vào Backstage (thêm vào `app-config.local.yaml`,
      xem `examples/app-config.local.yaml.snippet`)
- [ ] Vào UI → "Create..." → chọn "Hello Golden Path (test)"
- [ ] Điền form (modelName, modelVersion) → chạy → xem output log

**Đây là bước quan trọng nhất trong cả ngày** — bạn sẽ thấy tận mắt UI form
tự sinh ra từ YAML, không cần viết 1 dòng React nào. Đây chính là cơ chế
Backstage dùng để hiện thực hóa Golden Path.

## Cuối chiều (15-20 phút) — Dựng MLflow song song

```bash
bash scripts/setup-mlflow.sh
```

- [ ] MLflow UI chạy được ở `localhost:5000`
- [ ] Thử gọi API bằng curl (lệnh có sẵn trong output của script)

## Cuối ngày (30-45 phút) — Đọc trước cho ngày mai

- [ ] Đọc "Create a Backstage Plugin" (docs.backstage.io) — chỉ đọc, chưa code
- [ ] Ghi chú lại: chỗ nào bạn thấy khó hiểu nhất hôm nay, để hỏi/tra cứu tiếp

## Nếu bị kẹt

| Vấn đề thường gặp | Cách xử lý |
|---|---|
| `yarn dev` lỗi port đã dùng | Đổi port trong `app-config.local.yaml` hoặc kill process cũ |
| Node version không khớp | Dùng `nvm` để switch đúng version LTS |
| Docker MLflow không pull được image | Kiểm tra kết nối mạng, thử lại, hoặc dùng `pip install mlflow` chạy local thay vì Docker |
| Catalog không đọc được file YAML | Kiểm tra lại cấu hình `catalog.locations` trong `app-config.local.yaml` |

## Định nghĩa "xong việc" cho ngày 1

Bạn coi như đã đạt mục tiêu nếu tick được cả 4 mục checklist chính:
Backstage chạy ✅ · Entity hiện trong Catalog ✅ · Template chạy ra kết quả ✅ · MLflow UI mở được ✅
