# Kiến trúc tổng thể (tham chiếu nhanh)

Chi tiết đầy đủ nằm ở `playbook-ai-delivery-portal.md` (mục 4-6). File này chỉ
tóm tắt để tra cứu nhanh khi code.

```
┌────────────────────────────────────────────┐
│         Portal UI (Backstage)                 │  ← packages/app, packages/backend
├────────────────────────────────────────────┤
│   BFF / Orchestration API (FastAPI)            │  ← services/orchestration-api/ (tuần 4+)
│   - Auth (Keycloak) - Golden Path Engine        │
│   - Workflow trigger (Argo Workflows)           │
├───┬────────┬────────┬────────┬────────────┤
│Registry│Experiment│Inference│Notebook│      ← adapters/ (interface chung)
│Adapter │ Adapter  │ Adapter │Adapter │
├───┴────────┴────────┴────────┴────────────┤
│ MLflow │ MLflow   │ KServe/ │Kubeflow│      ← backend thật/mock
│Registry│ Tracking │BentoML  │Notebook│
└────────────────────────────────────────────┘
   Cross-cutting: OPA (policy) | Prometheus/Grafana | ArgoCD + Helm
```

## Nguyên tắc bất biến (đừng vi phạm khi code)

1. **Custom Scaffolder Action trong Backstage KHÔNG tự chứa logic nghiệp vụ** —
   nó chỉ gọi HTTP sang FastAPI Backend. Toàn bộ Adapter/Factory/Chain of
   Responsibility nằm ở Python (`services/orchestration-api/` khi tạo).
2. **Mọi Adapter implement chung 1 interface** (`IModelRegistryAdapter`,
   `IInferenceAdapter`...) — để đổi từ Mock sang Adapter thật của Viettel chỉ
   cần thêm 1 class mới, không sửa code đã có.
3. **2 Golden Path lõi**: Train→Track→Register, Register→Deploy. Không thêm
   golden path thứ 3 trừ khi 2 cái đầu đã ổn định (xem `roadmap.md`).

## Design pattern — nơi áp dụng

| Pattern | Ở đâu |
|---|---|
| Adapter | `adapters/*.py` — kết nối MLflow/KServe/hệ thống thật |
| Factory | `adapters/factory.py` — chọn đúng Adapter theo config |
| Template Method | Bản thân Backstage Scaffolder (`template.yaml` steps) — không cần tự code |
| Chain of Responsibility | `services/orchestration-api/policies/` — chuỗi policy check (OPA hoặc validation tay) |
