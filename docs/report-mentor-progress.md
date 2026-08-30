# Báo cáo tiến độ — AI Delivery Portal (MLOps/LLMOps)

> Viettel Digital Talent 2026 · Track Cloud. Nguồn: `docs/playbook-ai-delivery-portal.md`
> (v4) + `docs/mlops-lifecycle-software-template.md`. Cập nhật: 2026-08-27.

## 1. Tên đề tài & mô tả ngắn gọn

**AI Delivery Portal — nền tảng MLOps/LLMOps nội bộ dựng trên Backstage.**

Là **lớp nghiệp vụ (business logic layer)** cho vòng đời model AI, đứng
trên 6 sản phẩm AI Platform sẵn có
qua Adapter Pattern. Đóng vai trò "bộ não" quyết định **model nào đủ điều
kiện đưa vào dùng** (Evaluate Gate) và **theo dõi vòng đời model sau khi
deploy** (Monitor → Drift → Retrain) — không phải một cổng chuyển tiếp UI,
mà là nơi thật sự ra quyết định.

## 2. Triết lý thiết kế (Golden Path)

> **Golden Path = con đường được trải sẵn, dễ đi nhất, đã chuẩn hoá best
> practice — "làm đúng" là lựa chọn dễ nhất, không ép buộc tuyệt đối.**

```
Internal Developer Platform (IDP)   ← triết lý ("dev tự phục vụ")
        └── Golden Path             ← cách hiện thực hoá
                └── Backstage        ← công cụ cụ thể để build
```

6 nguyên tắc nền tảng: paved-road (không ép buộc) · giảm cognitive load ·
self-service · bắt đầu từ pain point thật · đo lường được · là sản phẩm
sống cần bảo trì.

**Quy tắc phân loại xuyên suốt mọi thiết kế** — cái gì hiện ra cho Dev
chọn, cái gì platform tự quyết:

| Loại đánh đổi | Ai quyết | Ví dụ |
|---|---|---|
| Nghiệp vụ/rủi ro (Dev cần hiểu & chịu trách nhiệm) | **Dev chọn** | thuật toán, deploy strategy, release strategy |
| Cơ chế ML/hạ tầng thuần kỹ thuật (có đáp án đúng-sai theo ngữ cảnh) | **Platform tự quyết** | feature scaling, chiến lược validation split |

**2 Golden Path đã có** (không có #3 — AI Notebook/hạ tầng generic là tính
năng Portal độc lập, không đóng khung thành golden path):

| | #1 — Train → Track → Register | #2 — Register → Deploy |
|---|---|---|
| Mục đích | Train/fine-tune → log MLflow Tracking → đăng ký Model Registry | Model qua Evaluate Gate mới được deploy lên KServe |
| Cơ chế | Argo WorkflowTemplate | orchestration-api gọi `evaluations/gate.py` rồi `KServeAdapter` |

## 3. Kiến trúc hệ thống

```
┌───────────────────────────────────────────────────────────────────────┐
│ Portal UI (Backstage) — packages/app-backstage + plugins/prompt-registry│
├───────────────────────────────────────────────────────────────────────┤
│ Orchestration API (FastAPI) — services/orchestration-api              │
│ auth/keycloak.py · evaluations/gate.py + llm_judge · routers/*        │
├───────────────┬───────────────┬───────────────┬───────────────┬───────┤
│   Registry    │   Inference   │   Workflow    │   VectorDB    │ LLM GW│
│   (MLflow)    │   (KServe)    │    (Argo)     │   (Qdrant)    │(LiteLLM)
└───────────────┴───────────────┴───────────────┴───────────────┴───────┘
                              Adapter Layer

Cross-cutting: Prometheus/Grafana · Keycloak
agents/mcp-servers/: mlops, k8s, metrics (Agent-ready qua MCP)
```

**Adapter Pattern — nguyên tắc bất biến của toàn dự án**: mỗi hệ thống con
(MLflow/KServe/Argo/Qdrant/LiteLLM/Feast/JupyterHub) có 1 interface trong
`adapters/interfaces.py`. Đổi Mock → backend thật chỉ cần thêm 1 class
implement interface — **không sửa code gọi** (router, Custom Scaffolder
Action). Đây cũng là nền có sẵn cho việc thêm hệ thống ngoài (vd CI/CD
generic) sau này mà không cần thiết kế lại.

**3 quy tắc điều phối bất biến** giữa UI và hệ thống:
1. Custom Scaffolder Action **không bao giờ** gọi thẳng adapter — chỉ gọi
   HTTP tới `orchestration-api`.
2. Router trong `orchestration-api` **không bao giờ** gọi thẳng SDK ngoài —
   luôn qua `adapters/interfaces.py`.
3. Ngoại lệ duy nhất: container chạy trong Argo Workflow (không có context
   Backstage) gọi thẳng `orchestration-api`.

## 4. MLOps Software Template — vấn đề hiện tại, thêm cái gì, đầu ra là gì

### Vấn đề hiện tại

2 Golden Path đang **hardcode cứng vào đúng 1 use case demo** (fraud
detection, cột `is_fraud`, 1 thuật toán `LogisticRegression`, 1 cách deploy
duy nhất) — chưa tổng quát hoá cho nhiều team/nhiều bài toán/nhiều loại
model như một nền tảng thật cần có.

### Thêm gì — tổng quát hoá theo 9 phase, thứ tự tuyến tính (mỗi phase phụ
thuộc phase trước, MLOps xong hết mới sang LLMOps)

| Phase | Nội dung thêm | Đầu ra |
|---|---|---|
| **1. Classical ML** (đã duyệt, sẵn sàng code) | `algorithm_registry.py` (~18 thuật toán: sklearn + XGBoost/LightGBM/CatBoost) theo 3 `taskType` (classification/regression/clustering); Evaluate Gate tổng quát theo `task_type`; Golden Path #1 mở từ 2 → 5 bước (`validate-dataset`, `model-summary`, publish PR thật); tự động chọn `TimeSeriesSplit` khi có `timeColumn` (chống rò rỉ dữ liệu tương lai) | Dev tự chọn task type + thuật toán qua dropdown, không đụng code |
| **2. Deploy Strategy** | `IDeployTrafficStrategy` (Direct/Canary/A-B/Blue-Green — dùng chung 1 cơ chế `canaryTrafficPercent` của KServe) + `IReleaseStrategy` (PR-gated/Instant) | Dev chọn chiến lược deploy/duyệt thay đổi qua dropdown |
| **3. Deep Learning** | `dl_architecture_registry.py` (MLP + LSTM qua PyTorch), tái dùng nguyên Evaluate Gate/Golden Path #2 | Dev chọn kiến trúc mạng + hyperparameter |
| **4. BYOC** ("Bring Your Own Code") | Contract cố định `def train(dataset, config) -> (model, metrics)`, Dev cung cấp Git repo, chạy trong cùng base image/ServiceAccount (không mở rộng bề mặt bảo mật) | Escape hatch cho nhu cầu ngoài preset, không cần đoán trước mọi framework |
| **5. HPO** | `IHyperparameterSearchStrategy` (Fixed/Grid/Random/Bayesian qua Optuna), chạy ngay trong pod Argo hiện có, log nested run vào MLflow | Dev nhập khoảng giá trị thay vì đoán tay 1 giá trị cố định |
| **6–7. NLP / CV** (roadmap, cần thiết kế chi tiết thêm) | Text classification (HuggingFace `Trainer`) / Image classification (torchvision) — phạm vi hẹp có chủ đích, dùng chung serving wrapper `mlflow.pyfunc.PythonModel` với BYOC | Mở rộng 2 domain phổ biến nhất ngoài dữ liệu bảng |
| **8. RecSys** | Golden Path hoàn toàn riêng (dataset là manifest tương tác user-item, gate theo ranking metric recall@k/NDCG, `servingMode` realtime/batch-precompute) | Golden Path #3 |
| **9. Model Monitoring** | Golden Path #4 — Argo CronWorkflow + Evidently, chỉ Data Drift v1, `onDriftDetected` (alert-only/auto-retrain, Dev-facing vì có rủi ro thật) | Khép kín vòng lặp Monitor → Drift → Retrain |
| — | **Reinforcement Learning** | Đánh giá kỹ, **không đưa vào roadmap** — phá vỡ mọi giả định nền tảng (không dataset tĩnh, không train 1 lần, không serving request/response) — giới hạn kiến trúc có chủ đích |
| — | **LLMOps** | Giữ nguyên DRAFT (`docs/llmops-lifecycle-plan-draft.md`), chỉ bắt đầu sau khi 9 phase MLOps trên hoàn thành |

**Thiết kế xuyên suốt mọi phase (không phải 1 phase riêng)**: Data
Quality/EDA — registry check theo `task_type` (universal: missing
values/duplicate rows; đặc thù: leakage-tương-quan, class imbalance, gap
time-series, ảnh hỏng, sparsity RecSys...), chặn sớm ở bước
`validate-dataset` trước khi tốn tài nguyên train.

### Đầu ra cụ thể cho Dev khi dùng Golden Path

1. Mở Software Template trên Backstage UI, điền form (task type → thuật
   toán/kiến trúc → hyperparameter/HPO → deploy/release strategy).
2. Theo dõi tiến trình real-time ngay trên Task page — không cần rời khỏi
   Portal để mở MLflow/Argo UI gốc.
3. Nhận kết quả: model đã đăng ký vào Model Registry kèm metric thật, PR
   catalog/manifest sẵn để review, hoặc model đã deploy trực tiếp (tuỳ
   `releaseStrategy`).
4. Toàn bộ pipeline phía sau (registry pattern, Adapter Pattern, Evaluate
   Gate, MLflow tracking) tái sử dụng nguyên vẹn qua từng phase — mở rộng
   khả năng, không phải viết lại kiến trúc.
