# SỔ TAY THAM CHIẾU CỦA CƯỜNG (v3)
## AI Delivery Portal — GitOps for Model (MLOps/LLMOps)
### Viettel Digital Talent 2026 · Track Cloud · Phase 2

> **Thay đổi lớn nhất so với bản trước**: Đề tài đã được mentor CHÍNH THỨC tách thành 2 sản phẩm chạy song song, dùng chung 1 bức tranh lớn nhưng KHÁC repo, khác người bảo vệ. Sổ tay này viết lại toàn bộ phần định vị/kiến trúc/scope cho đúng ranh giới mới.

---

## 1. LA BÀN — CÁC CÂU HỎI CỐT LÕI

1. **Việc gì lặp lại thường xuyên nhất?** (Frequency)
2. **Việc gì dễ sai nhất?** (Error-proneness)
3. **Việc gì có rủi ro cao nhất nếu làm sai?** (Impact/Blast radius)
4. **Thiết kế này có dễ expose thành tool cho agent sau này không?** (Agent-readiness)

### Ma trận ưu tiên
```
                    Rủi ro thấp              Rủi ro cao
Tần suất cao   │  Tự động hóa nhẹ nhàng  │  ƯU TIÊN SỐ 1
Tần suất thấp  │  Ưu tiên thấp nhất      │  Stretch goal
```

---

## 2. ĐỊNH VỊ ĐỀ TÀI — BỨC TRANH 2 SẢN PHẨM

```
┌─────────────────────────────────────────────────────────┐
│ Phase 1 — netCI Delivery Platform (Hiếu)                │
│ = NỀN TẢNG CI/CD GENERIC, dùng cho MỌI project          │
│                                                         │
│ - Pipeline-as-Code (Jenkins Shared Library, form UI)    │
│ - Jenkins config quản lý bằng Git (IaC, tái lập được)   │
│ - Ephemeral agent (Jenkins Kubernetes Plugin) cô lập    │
│   theo project, thay workspace dùng chung               │
│ - Deploy đa hạ tầng (Systemd/Docker/K8s) qua Ansible +  │
│   Helm, có Dev/Staging/Prod, approval, audit            │
│ - Vận hành đa cụm Jenkins, SBOM, ký artifact, dashboard │
│   DORA                                                  │
└─────────────────────────────────────────────────────────┘
                            │ Cường GỌI VÀO qua API/Adapter
                            │ (netci_adapter.py) — KHÔNG tự dựng
                            │ Jenkins, KHÔNG tự học multi-cluster/SBOM
                            ▼
┌─────────────────────────────────────────────────────────┐
│ Phase 2 — GitOps for Model / AI Delivery Portal (Cường) │
│ = LỚP NGHIỆP VỤ đặc thù MLOps/LLMOps                    │
│                                                         │
│ - Backstage UI + Adapter Pattern tích hợp 4 sản phẩm    │
│   AI Platform (Registry/Experiment/Inference/Notebook)  │
│ - Golden Path #1: Train → Track → Register              │
│ - Golden Path #2: Register → Deploy (quyết định GÌ được │
│   phép lên Git — Evaluate Gate, không phải cơ chế sync) │
│ - Vòng lặp Monitor → Drift → Retrain (đặc thù ML, netCI │
│   generic không có khái niệm này)                       │
│ - Agent-ready: MCP servers + Skills                     │
└─────────────────────────────────────────────────────────┘
```

### Câu chuyện định vị (dùng khi bảo vệ)

> *"netCI (Hiếu) là ĐỘNG CƠ — cơ chế CI/CD kỹ thuật tổng quát, dùng được cho bất kỳ loại project nào. AI Delivery Portal / GitOps for Model (Cường) là BỘ NÃO cho riêng domain MLOps — quyết định model nào đủ điều kiện lên Git (Evaluate Gate), theo dõi vòng đời model sau khi deploy (Drift→Retrain) — những khái niệm không tồn tại trong CI/CD generic. Em không tự xây lại cơ chế deploy/agent/multi-cluster — không TIÊU THỤ nó qua Adapter Pattern, đúng kiến trúc đã thiết kế từ đầu."*

### So sánh GitOps thông thường vs GitOps for Model

netCI làm "GitOps" ở mức cơ chế (sync hạ tầng generic); phần của Cường **không trùng lặp** — vì hai bên khác nhau về bản chất, không chỉ khác tên gọi:

| | GitOps thông thường | GitOps for Model |
|---|---|---|
| **Đối tượng quản lý** | Ứng dụng / hạ tầng (image, replicas, config) | Model ML (version, chất lượng dự đoán, dữ liệu huấn luyện) |
| **Điều kiện "đủ tốt để deploy"** | Vượt qua kiểm thử kỹ thuật (build, security scan) | Vượt qua đánh giá chất lượng (Evaluate Gate — accuracy/LLM-as-judge) |
| **Truy vết (lineage)** | Commit code → image | Code + dữ liệu huấn luyện + tham số → model |
| **Vòng đời sau deploy** | Ổn định cho tới khi có bản vá mới | Suy giảm dần theo thời gian (drift) — cần giám sát & huấn luyện lại |
| **Rollback bảo vệ điều gì** | Tính đúng đắn kỹ thuật (không lỗi/crash) | Chất lượng dự đoán thực tế (accuracy) |

---

## 3. GOLDEN PATH — KHÁI NIỆM NỀN TẢNG

> **Golden Path = con đường được trải sẵn, dễ đi nhất, đã chuẩn hóa best-practice — "làm đúng" là lựa chọn dễ nhất, không ép buộc tuyệt đối.**

```
Internal Developer Platform (IDP)   ← triết lý ("dev tự phục vụ")
        └── Golden Path             ← cách hiện thực hóa
                └── Backstage        ← công cụ cụ thể để build
```

### 6 nguyên tắc nền tảng
1. "Paved road, not the only road" — khuyến nghị, không ép buộc tuyệt đối
2. Giảm cognitive load — hệ thống "nhớ hộ" best-practice
3. Self-service — dev tự làm được ngay
4. Bắt đầu từ pain point thật
5. Đo lường được (adoption, thời gian, số lỗi giảm)
6. Là sản phẩm sống, cần bảo trì

### 2 Golden Path hiện tại

Chốt đúng **2 golden path**, không có #3 — AI Notebook và provisioning hạ tầng generic là tính năng Portal độc lập, không đóng khung thành golden path.

| | #1 — Train → Track → Register | #2 — Register → Deploy |
|---|---|---|
| **Mục đích** | Huấn luyện (hoặc fine-tune) → log vào MLflow Tracking → đăng ký Model Registry | Model đủ điều kiện (qua Evaluate Gate) mới được deploy lên KServe |
| **Template** | `examples/templates/train-track-register/template.yaml` | `examples/templates/register-deploy/template.yaml` |
| **Cơ chế chạy** | Argo WorkflowTemplate `train-register-golden-path`, hoặc `fine-tune-golden-path` khi có `baseModelUri` | Orchestration API gọi `evaluations/gate.py` (LLM-as-judge) trước khi gọi `KServeAdapter` |
| **Trạng thái** | Template còn mock (`debug:log`), chưa nối Custom Action thật | Template còn mock (`debug:log`), chưa nối Custom Action thật |

### Kế hoạch tiếp theo — Software Template & Catalog

1. **Orchestration API** (`routers/models.py`, mới) — `/register-model`,
   `/trigger-training`, `/policy-check`. Làm trước, đang chặn các bước sau.
2. **4 Custom Action** (`packages/backend/`, chỉ gọi HTTP sang API trên):
   - `orchestration:trigger-training` → Argo
   - `orchestration:register-model` → MLflow
   - `orchestration:policy-check` → Evaluate Gate
   - `orchestration:deploy-model` → **commit Git** → ArgoCD sync (đúng GitOps, không gọi K8s trực tiếp)
3. Nối 4 action vào 2 template (thay `debug:log`).
4. **Catalog**: thêm action `catalog:register` cuối Golden Path #1 → tự sinh entity thật thay vì file demo.
5. **Test**: `docker compose up -d` → verify từng endpoint qua curl/Postman → verify lại qua Scaffolder UI.
6. **IDP tham khảo** (theo yêu cầu mentor) — không nền tảng nào làm đúng golden path này, gần nhất là AWS:
   - [AWS: Backstage + SageMaker AIOps](https://docs.aws.amazon.com/prescriptive-guidance/latest/patterns/accelerate-mlops-with-backstage-and-sagemaker-templates.html) — cùng kiến trúc Backstage+Template+Adapter, nhưng dừng ở provisioning hạ tầng, không có Evaluate Gate/dataset lineage.
   - [Red Hat Developer Hub — AI templates](https://github.com/redhat-developer/red-hat-developer-hub-software-templates) — golden path AI của họ là scaffold app GenAI (chatbot, RAG...), không phải MLOps train/register/deploy.
   - [Port — Blueprints](https://docs.getport.io/build-your-software-catalog/define-your-data-model/setup-blueprint/) & [Scorecards](https://docs.port.io/promote-scorecards/usage/) — không có blueprint ML dựng sẵn, Scorecard là rules engine generic, phải tự cấu hình.
   - [Cortex — Internal Developer Portal](https://www.cortex.io/post/what-is-an-internal-developer-portal) — "ML model" chỉ là 1 loại entity liệt kê ngang Kafka topic/Docker image, không có lifecycle riêng.

### Nguyên tắc thiết kế UI/UX

> **"Một Portal duy nhất — không phải tập hợp các UI rời rạc. Dev chỉ chạm vào UI gốc của hệ thống con (netCI/Jenkins, MLflow...) khi chủ động muốn đào sâu chi tiết."**

**Vì sao:** đúng tinh thần Backstage — Portal là *single pane of glass*, không phải cổng trung chuyển. Theo nghiên cứu UX cho IDP (Kirsten Schwarzer, "Designing for Success: UX Principles for IDP", KubeCon), khi vẽ user journey map cho onboarding, ma sát (friction) lớn nhất tập trung đúng ở *touchpoint* — chỗ dev phải nhảy qua lại giữa nhiều UI khác nhau để hoàn thành 1 tác vụ. Gộp về 1 Portal là cách trực tiếp triệt tiêu điểm ma sát này, không chỉ là lựa chọn thẩm mỹ.

- Dev KHÔNG BAO GIỜ cần mở UI gốc của netCI/Jenkins để thao tác (trigger, theo dõi trạng thái).
- Trạng thái/log **nhúng (embed) trực tiếp** trong Portal — không deep-link đưa Dev rời khỏi Portal.
- Log lỗi hiển thị trong Portal theo nguyên tắc "error là proxy của frustration" (Jared Spool, trích trong cùng talk): nêu rõ **chuyện gì xảy ra, vì sao, và bước tiếp theo cần làm** — không chỉ dump nguyên console gốc.
- Áp dụng: `netci_adapter.get_console_log_stream()` (qua Adapter Pattern) trả log stream về, Portal render ngay trong trang Catalog của model/component đó.

---

## 4. KIẾN TRÚC HỆ THỐNG

```
┌───────────────────────────────────────────────────────────────────────────────────────────────┐
│ Portal UI (Backstage) — packages/app-backstage                                                │
│ + plugins/prompt-registry                                                                     │
├───────────────────────────────────────────────────────────────────────────────────────────────┤
│ Orchestration API (FastAPI) — services/orchestration-api                                      │
│ - auth/keycloak.py    - evaluations/gate.py + llm_judge                                       │
│ - routers/chat.py, prompts.py                                                                 │
├───────────────┬───────────────┬───────────────┬───────────────┬───────────────┬───────────────┤
│   Registry    │   Inference   │   Workflow    │   VectorDB    │    LLM GW     │     netCI     │
│   (MLflow)    │   (KServe)    │    (Argo)     │   (Qdrant)    │   (LiteLLM)   │ (gọi vào Hiếu │
│               │               │               │               │               │ — mock trước) │
└───────────────┴───────────────┴───────────────┴───────────────┴───────────────┴───────────────┘
  Adapter Layer

Cross-cutting: Prometheus/Grafana | Keycloak
agents/mcp-servers/: mlops, k8s, metrics (3 server)
```

### Adapter Pattern — nguyên tắc bất biến

```python
# adapters/interfaces.py — đã implement đúng trong repo
class IModelRegistryAdapter(ABC):
    def register_model(...) -> dict: ...
    def list_models(...) -> list[dict]: ...
    def get_model_metrics(...) -> dict: ...

class IInferenceAdapter(ABC): ...
class IWorkflowAdapter(ABC): ...
class IVectorStoreAdapter(ABC): ...
class ILLMGatewayAdapter(ABC): ...

# CẦN THÊM (còn thiếu trong repo — việc tiếp theo):
class ICIExecutorAdapter(ABC):
    """Gọi vào netCI (Hiếu) để trigger/theo dõi pipeline generic.
    Giữ MOCK cho tới khi Hiếu có API thật — KHÔNG chờ Hiếu để tiếp
    tục phát triển Golden Path."""
    def trigger_job(self, job_config) -> JobHandle: ...
    def get_job_status(self, job_handle) -> JobStatus: ...
    def get_console_log_stream(self, job_handle): ...
```

---

## 5. BỐ CỤC SLIDE BẢO VỆ

```
1. Trang bìa (ghi rõ: Phase 2 — GitOps for Model, song song với netCI của Hiếu)
2. Bối cảnh AI Platform + vị trí trong bức tranh 2 sản phẩm (sơ đồ mục 1)
3. ⭐ Vấn đề thật (pain point — bổ sung số liệu Qwen/fine-tune nếu có)
4. Giải pháp tổng quan — nhấn: "netCI là động cơ, mình là bộ não MLOps"
5. Kiến trúc hệ thống (sơ đồ mục 4, có nhánh Agent Interface — MCP)
6. Adapter Pattern — minh chứng bằng code thật (interfaces.py)
7. Golden Path #1 (Argo Workflows)
8. Golden Path #2 (trọng tâm) — Evaluate Gate LLM-as-judge, GitOps sync
9. LLMOps active: Vector DB + LLM Gateway + Prompt Registry (case thật: Qwen)
10. Demo (live + video backup)
11. Benchmark thời gian/số bước
12. Dashboard observability
13. (nếu MCP ổn định) Demo agent gọi Golden Path qua MCP
14. Giới hạn hiện tại — nêu rõ phần phụ thuộc netCI đang mock
15. Roadmap Production
16. Kết luận
```

---

## 6. CÂU TRẢ LỜI MẪU CHO CÂU HỎI KHÓ

**Q: "Sao không tự làm Jenkins/CI-CD, lại đi gọi qua netCI của người khác?"**
> "Việc chuẩn hóa CI/CD generic (multi-cluster Jenkins, ephemeral agent, SBOM) là bài toán hạ tầng tổng quát — Adapter Pattern của em cho phép tách biệt rõ: em tập trung vào NGHIỆP VỤ đặc thù MLOps (Evaluate Gate, Drift→Retrain) là nơi tạo giá trị khác biệt, còn cơ chế thực thi generic thì tái sử dụng, tránh trùng lặp công sức với đề tài netCI đang chạy song song."

**Q: "Nếu netCI của Hiếu chưa xong, Portal của em có chạy được không?"**
> "Có — `netci_adapter.py` được thiết kế mock hoàn chỉnh ngay từ đầu, đúng nguyên tắc Adapter Pattern đã áp dụng cho mọi hệ thống con khác. Golden Path của em không phụ thuộc tiến độ netCI để phát triển và demo."

**Q: "Golden path của em dừng ở Deploy, model xuống cấp thì sao?"**
> "Em đã có `agents/skills/evaluate_drift.py` làm nền cho vòng lặp Retrain — phần trigger tự động nằm trong roadmap, nhưng cơ chế phát hiện drift đã có sẵn."

**Q: "Sao lại thêm MCP/Agent, đề bài đâu có yêu cầu?"**
> "Orchestration API thiết kế theo Facade Pattern — thêm kênh truy cập cho AI Agent gần như không phát sinh rủi ro kiến trúc. Đây là minh chứng cho việc thiết kế Adapter/Facade từ đầu là đúng đắn, đón đầu xu hướng Agentic Platform Engineering."

 
---

## 7. NGUYÊN TẮC GHI NHỚ TỔNG QUÁT

1. Luôn quay lại **4 câu hỏi cốt lõi** (mục 1)
2. Chiều sâu > chiều rộng — **Golden Path #2 là ưu tiên số 1 hiện tại**, không mở rộng MCP thêm cho tới khi #2 xong
3. Mọi thiết kế phải có lý do — kể cả lý do KHÔNG dùng 1 công nghệ (Temporal/Kusion/Crossplane) cũng cần ghi lại, không chỉ lý do có dùng
4. Chủ động nêu giới hạn — đặc biệt phần đang mock chờ netCI
5. **Adapter Pattern là bảo hiểm — áp dụng cho CẢ hệ thống anh em (netCI), không chỉ hệ thống AI Platform**
6. Nghĩ như Platform Engineer thật — golden path giải quyết pain point thật, đo lường được, có đường tới production
7. Agent-ready là triết lý thiết kế, nhưng **không được lấn át việc hoàn thiện Golden Path lõi** — 3 MCP server hiện tại là tín hiệu cần tự kiểm tra lại ưu tiên.

---

**Cập nhật lần 3, sau khi:** 

- (a) mentor phân Phase rõ ràng giữa Cường (GitOps for Model) và Hiếu (netCI Delivery Platform); 
- (b) soát trực tiếp repo thật `AI-delivery-portal`.