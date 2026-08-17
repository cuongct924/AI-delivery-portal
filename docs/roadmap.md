# Roadmap 12 tuần (bản theo dõi tiến độ)

Copy từ playbook, dùng để tick tiến độ trực tiếp trong repo (commit định kỳ).

- [ ] **Tuần 1** — Backstage + MLflow test-drive (ngày 1 xong). Đọc khái niệm
      Golden Path/IDP. Hỏi mentor (checklist riêng trong playbook mục 10).
- [ ] **Tuần 2-3** — Setup lab đầy đủ: Mock Inference (FastAPI), viết
      `IModelRegistryAdapter` interface + `MLflowRegistryAdapter`. Custom
      Scaffolder Action đầu tiên gọi thật tới MLflow.
- [ ] **Tuần 4-5** — Viết Adapter thật cho hệ thống Viettel (nếu được cấp
      quyền). Dựng `services/orchestration-api/` (FastAPI).
- [ ] **Tuần 6-7** — Golden Path #1: Train → Track → Register (Argo Workflows).
- [ ] **Tuần 8-9** — Golden Path #2: Register → Deploy (Helm + ArgoCD + policy
      check — OPA nếu kịp, validation tay nếu không).
- [ ] **Tuần 10** — Dashboard observability (Prometheus/Grafana). Bắt đầu benchmark.
      Stretch: Rollback (nếu dư thời gian).
- [ ] **Tuần 11** — Hoàn thiện benchmark, viết báo cáo, slide, quay video demo backup.
- [ ] **Tuần 12** — Thuyết trình thử với mentor, chỉnh sửa, chuẩn bị Q&A.

## Mốc cắt lỗ (tự kiểm tra hàng tuần)

| Nếu tới... | Mà chưa... | Thì... |
|---|---|---|
| Tuần 3 | Chạy được 1 custom Backstage plugin | Chuyển sang Portal tự viết bằng React thuần |
| Tuần 6 | Golden Path #1 xong | Bỏ hẳn nhánh LLMOps mở rộng (Prompt Registry/RAG) |
| Tuần 9 | Golden Path #2 có policy check | Bỏ OPA, thay bằng validation logic tay trong FastAPI |
| Tuần 10 | Có ít nhất 1 bộ benchmark | Ưu tiên tuyệt đối benchmark tự đo thủ công vs Portal |
