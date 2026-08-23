# SỔ TAY THAM CHIẾU (v3)
## AI Delivery Portal — GitOps for Model (MLOps/LLMOps)
### Viettel Digital Talent 2026 · Track Cloud · Phase 2 — Cường
### Repo song song: netCI Delivery Platform (Hiếu) — Phase 1

> **Thay đổi lớn nhất so với bản trước**: đề tài đã được mentor CHÍNH THỨC tách thành 2 sản phẩm chạy song song, dùng chung 1 bức tranh lớn nhưng KHÁC repo, khác người bảo vệ. Sổ tay này viết lại toàn bộ phần định vị/kiến trúc/scope cho đúng ranh giới mới. Các phần Temporal/Kusion/Crossplane/tự vận hành Jenkins đã được đánh giá lại và HẠ CẤP xuống "đã cân nhắc, không thuộc phạm vi của Cường" — không xóa để giữ lại lý do quyết định.

---

## 0. LA BÀN — 4 CÂU HỎI CỐT LÕI (giữ nguyên, dùng xuyên suốt)

1. **Việc gì lặp lại thường xuyên nhất?** (Frequency)
2. **Việc gì dễ sai nhất?** (Error-proneness)
3. **Việc gì có rủi ro cao nhất nếu làm sai?** (Impact/Blast radius)
4. **Thiết kế này có dễ expose thành tool cho agent sau này không?** (Agent-readiness) — áp dụng từ Tuần 1, gần như miễn phí (chỉ là kỷ luật thiết kế API rõ ràng)

### Ma trận ưu tiên
```
                    Rủi ro thấp              Rủi ro cao
Tần suất cao   │  Tự động hóa nhẹ nhàng  │  ƯU TIÊN SỐ 1
Tần suất thấp  │  Ưu tiên thấp nhất       │  Stretch goal
```

### Câu hỏi lọc thứ 5 — MỚI, dùng khi phân vai với Hiếu
5. **"Việc này là NGHIỆP VỤ đặc thù MLOps (của mình) hay CƠ CHẾ HẠ TẦNG TỔNG QUÁT (của netCI)?"** — mọi tính năng mới trước khi code phải trả lời được câu này. Nếu là cơ chế tổng quát (multi-cluster, ephemeral agent, IaC Jenkins, ký artifact...) → KHÔNG tự làm, gọi API netCI qua Adapter.

---

## 1. ĐỊNH VỊ ĐỀ TÀI — BỨC TRANH 2 SẢN PHẨM

```
┌─────────────────────────────────────────────┐
│  Phase 1 — netCI Delivery Platform (Hiếu)         │
│  = NỀN TẢNG CI/CD GENERIC, dùng cho MỌI project      │
│  - Pipeline-as-Code (Jenkins Shared Library, form UI) │
│  - Jenkins config quản lý bằng Git (IaC, tái lập được) │
│  - Ephemeral agent (Jenkins Kubernetes Plugin) cô lập  │
│    theo project, thay workspace dùng chung              │
│  - Deploy đa hạ tầng (Systemd/Docker/K8s) qua Ansible +  │
│    Helm, có Dev/Staging/Prod, approval, audit             │
│  - Vận hành đa cụm Jenkins, SBOM, ký artifact, dashboard   │
│    DORA                                                     │
└──────────────────────┬────────────────────────┘
                        │ Cường GỌI VÀO qua API/Adapter
                        │ (netci_adapter.py) — KHÔNG tự dựng
                        │ Jenkins, KHÔNG tự học multi-cluster/SBOM
                        ▼
┌─────────────────────────────────────────────┐
│  Phase 2 — GitOps for Model / AI Delivery Portal   │
│  (Cường — CHÍNH BẠN)                                 │
│  = LỚP NGHIỆP VỤ đặc thù MLOps/LLMOps                  │
│  - Backstage UI + Adapter Pattern tích hợp 4 sản phẩm   │
│    AI Platform (Registry/Experiment/Inference/Notebook)  │
│  - Golden Path #1: Train→Track→Register                  │
│  - Golden Path #2: Register→Deploy (quyết định GÌ được    │
│    phép lên Git — Evaluate Gate, không phải cơ chế sync)   │
│  - Vòng lặp Monitor→Drift→Retrain (đặc thù ML, netCI       │
│    generic không có khái niệm này)                           │
│  - Agent-ready: MCP servers + Skills                          │
└─────────────────────────────────────────────┘
```

### Câu chuyện định vị (dùng khi bảo vệ)

> *"netCI (Hiếu) là ĐỘNG CƠ — cơ chế CI/CD kỹ thuật tổng quát, dùng được cho bất kỳ loại project nào. AI Delivery Portal / GitOps for Model (em) là BỘ NÃO cho riêng domain MLOps — quyết định model nào đủ điều kiện lên Git (Evaluate Gate), theo dõi vòng đời model sau khi deploy (Drift→Retrain) — những khái niệm không tồn tại trong CI/CD generic. Em không tự xây lại cơ chế deploy/agent/multi-cluster — em TIÊU THỤ nó qua Adapter Pattern, đúng kiến trúc đã thiết kế từ đầu."*

### Vì sao KHÔNG nên thấy phần của mình "ít" — đã phân tích kỹ, kết luận:

Nếu netCI làm hẳn "GitOps" ở mức cơ chế (ArgoCD sync, Helm templating generic), phần của Cường **KHÔNG BỊ MẤT GIÁ TRỊ** — vì GitOps generic (Cường/netCI làm) khác hoàn toàn "GitOps for Model" (đặc thù):

| GitOps thông thường (netCI) | GitOps for Model (Cường — giữ lại) |
|---|---|
| Deploy dựa trên image version, replicas, resource limit | Deploy dựa trên **model version + accuracy threshold + dataset lineage** |
| Policy: security scan, resource limit (mọi app) | Policy ĐẶC THÙ: **model đã qua Evaluate Gate (LLM-as-judge) chưa** |
| Rollback: quay lại version code | Rollback: quay lại **version MODEL**, kèm Canary dựa trên accuracy thực tế |
| Không có khái niệm "model xuống cấp" | **Drift→Retrain loop** — vòng lặp riêng của ML, netCI generic không có |

---

## 2. GOLDEN PATH — KHÁI NIỆM NỀN TẢNG (giữ nguyên, đã kiểm chứng đúng qua repo)

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

### Nguyên tắc UX bổ sung — MỚI (theo yêu cầu mentor cho riêng lớp thực thi)

> **"Ở 1 cái Portal, không phải Jenkins/netCI. Chỉ dùng lõi Jenkins/netCI nếu Dev chủ động muốn xem chi tiết."**

- Dev KHÔNG BAO GIỜ cần mở UI gốc của netCI/Jenkins để thao tác.
- Trạng thái/log phải **nhúng (embed) trực tiếp** trong Portal — không dùng deep-link đưa Dev rời khỏi Portal.
- Log chi tiết (console output gốc) vẫn xem được, nhưng **qua giao diện Portal**, không chuyển hẳn sang domain khác.
- Áp dụng: `netci_adapter.get_console_log_stream()` nhúng log ngay trong trang Catalog.

---

## 3. VÒNG ĐỜI MODEL — ẢNH HƯỞNG THIẾT KẾ (giữ nguyên, đã hiện thực hóa trong repo)

```
Train → Experiment → Evaluate → Register → Deploy → Monitor → Retrain ─┐
  ↑                                                                      │
  └──────────────────────────────────────────────────────────────────┘
```

| Domain Knowledge | Golden Path bị ảnh hưởng | Trạng thái trong repo |
|---|---|---|
| Model versioning ≠ Code versioning | #1 Register — metadata cần git_commit_hash + dataset_version + hyperparameters | ✅ `dataset_version` (DVC md5, `data/*.dvc`) ghi vào `mlflow_adapter.py::register_model()`; `git_commit_hash`/`hyperparameters` còn thiếu |
| Evaluate là gate ẩn — insight tự phát hiện | Giữa Experiment và Register | ✅ `evaluations/gate.py` + `evaluations/llm_judge.py` (LLM-as-judge, KHÔNG chỉ threshold đơn giản) |
| Adversarial/Red-team testing (LLMOps, ch.13 sách MLPE) | Mở rộng Evaluate Gate — chặn model/prompt "bẻ được" (jailbreak) trước khi lên Git | ⚠️ Chưa có — cần thêm bộ test tấn công vào `gate.py`, xem mục 7 |
| Model drift | Deploy → Monitor | ✅ `agents/skills/evaluate_drift.py` |
| Prompt versioning (LLMOps) | Registry mở rộng | ✅ `plugins/prompt-registry/` (Backstage plugin riêng) |
| RAG (LLMOps) | Kiến trúc tổng thể | ✅ `adapters/vector_db_adapter.py` (Qdrant) |
| LLM Gateway (multi-model, cost tracking) | LLMOps mở rộng | ✅ `adapters/llm_gateway_adapter.py` (LiteLLM) |

### LLMOps — CHUYỂN TỪ "roadmap only" SANG "ACTIVE SCOPE" (đã xác nhận nhu cầu thật)

Đã xác nhận với Viettel: **đang serving Qwen cho nhiều team, có dịch vụ fine-tune riêng, có người theo dõi chi phí token/API**. Đây không còn là giả định — Vector DB Adapter + LLM Gateway Adapter + Prompt Registry Plugin đã lên trong repo là đúng hướng, **giữ nguyên, không cắt**.

---

## 4. KIẾN TRÚC HỆ THỐNG (đối chiếu đúng repo thật)

```
┌────────────────────────────────────────────────────┐
│         Portal UI (Backstage) — packages/app-backstage │
│         + plugins/prompt-registry                        │
├────────────────────────────────────────────────────┤
│   Orchestration API (FastAPI) — services/orchestration-api│
│   - auth/keycloak.py   - evaluations/gate.py + llm_judge  │
│   - routers/chat.py, prompts.py                            │
├───┬────────┬────────┬────────┬────────┬────────┬──┤
│Registry│Inference│Workflow│VectorDB│LLM GW │netCI │ Adapter
│(MLflow)│(KServe) │(Argo)  │(Qdrant)│(LiteLLM)│(GỌI VÀO│ Layer
│        │         │        │        │        │Hiếu — │
│        │         │        │        │        │MOCK trước│
└────┴────────┴────────┴────────┴────────┴────────┴──┘
   Cross-cutting: Prometheus/Grafana | Keycloak
   agents/mcp-servers/: mlops, k8s, metrics (3 server, xem cảnh báo mục 7)
```

### Adapter Pattern — nguyên tắc bất biến (đã có code thật, giữ nguyên 100%)

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

## 5. TECH STACK — ĐÃ SOÁT LẠI THEO REPO THẬT + RANH GIỚI VỚI HIẾU

| Layer | Công nghệ (repo thật) | Ai sở hữu |
|---|---|---|
| Portal UI | Backstage (`packages/app-backstage`, `packages/backend`) | ✅ Cường |
| Orchestration API | FastAPI (`services/orchestration-api`) | ✅ Cường |
| Auth | Keycloak | ✅ Cường (dùng cho Portal), netCI có thể có auth riêng cho Jenkins |
| Model Registry + Experiment | MLflow | ✅ Cường |
| Inference | KServe | ✅ Cường |
| Pipeline Golden Path #1 | **Argo Workflows** (`infra/argo-workflows/train-register-template.yaml`) | ✅ Cường — ĐÂY LÀ QUYẾT ĐỊNH CHỐT LẠI: Cường tự orchestrate phần train/evaluate (đặc thù ML), KHÔNG cần Jenkins trực tiếp cho việc này |
| Vector DB (RAG) | Qdrant | ✅ Cường |
| LLM Gateway | LiteLLM | ✅ Cường |
| CI/CD generic, multi-cluster, IaC Jenkins, ephemeral agent | **Jenkins** (qua netCI) | ❌ **Hiếu** — Cường chỉ gọi qua `netci_adapter.py` |
| Deploy đa hạ tầng (Systemd/Docker/K8s qua Ansible) | **netCI Deploy Engine** | ❌ **Hiếu** — Cường gọi vào khi cần deploy thật lên hạ tầng ngoài K8s |
| GitOps sync cơ chế (ArgoCD, Helm packaging cho KServe) | Cường tự phát triển trước (Canary theo accuracy — đặc thù ML, không chỉ health check generic); tích hợp/bàn giao vào netCI Deploy Engine sau khi ổn định | ✅ Cường (đã chốt — xem mục 9) |
| Policy (model-specific: Evaluate Gate) | Custom logic + LLM-as-judge | ✅ Cường |
| Policy (generic: resource limit, security scan) | OPA (nếu netCI cung cấp) hoặc tự làm nhẹ | ⚠️ Cần hỏi Hiếu |
| Observability | Prometheus + Grafana | ✅ Cường |
| Agentic Interface | MCP (3 server: mlops/k8s/metrics), Skills | ✅ Cường (xem cảnh báo scope mục 7) |

### Công nghệ ĐÃ CÂN NHẮC nhưng KHÔNG đưa vào stack — lý do giữ lại để nhớ

| Công nghệ | Vì sao từng cân nhắc | Vì sao KHÔNG dùng |
|---|---|---|
| Crossplane | Kiến trúc "control plane vạn năng", CNCF Graduated 10/2025 | Chồng lấn ArgoCD/Helm, effort học không tương xứng; nhắc ở Roadmap |
| Temporal | Giải quyết đúng vấn đề "chờ Approve lâu, không mất trạng thái" (durable workflow) | Sau khi rõ ranh giới với Hiếu: đây là bài toán tầng orchestration TỔNG QUÁT, nếu cần "chờ lâu" nên hỏi netCI có hỗ trợ không, KHÔNG tự dựng Temporal riêng |
| Kusion | Hỗ trợ deploy cả K8s lẫn non-K8s (systemd/Ansible) | Đây CHÍNH LÀ phạm vi "netCI Deploy Engine (Ansible/Helm đa hạ tầng)" của Hiếu — không cần Cường tự làm |
| Jenkins (tự vận hành trực tiếp) | Ban đầu tưởng phải tự học Kubernetes Plugin, Shared Library | Sau khi phân vai rõ: Jenkins hoàn toàn thuộc netCI (Hiếu), Cường chỉ gọi API |
| Semantic Caching (Redis) | Tối ưu chi phí gọi LLM (ch.13 sách MLPE, Cost optimization) | Cơ chế tối ưu generic, không phải nghiệp vụ MLOps đặc thù; `chat.py` còn là stub — chưa có RAG thật để đo nhu cầu cache. Làm sau khi RAG chạy thật và có số liệu request trùng lặp |
| NeMo Guardrails (sidecar K8s) | Input/output filter an toàn cho LLM (ch.13 sách MLPE, Governance) | Kiến trúc hạ tầng tổng quát, cùng nhóm với OPA ("⚠️ Cần hỏi Hiếu" ở bảng trên); nếu cần chặn PII/từ khóa cấm, chỉ nên viết 1 hàm filter nhỏ ngay trong `chat.py` — không dựng sidecar lúc Golden Path #2 chưa xong |

---

## 6. DESIGN PATTERN — ĐÃ HIỆN THỰC HÓA TRONG REPO

| Pattern | Áp dụng ở đâu (file thật) | Trạng thái |
|---|---|---|
| **Adapter** | `adapters/interfaces.py` + 6 implementation | ✅ Đã code |
| **Template Method** | Backstage Scaffolder (`examples/templates/hello-golden-path/`) | ✅ Đã có |
| **Chain of Responsibility** | `evaluations/gate.py` (safety/correctness/relevance thresholds nối tiếp) | ✅ Đã code, cần mở rộng thêm netCI policy khi có |
| **Factory** | Chọn Adapter theo config (mock vs thật) | ⚠️ Cần rà lại — kiểm tra có factory rõ ràng chưa hay đang hardcode |

---

## 7. SCOPE — CẢNH BÁO THỰC TẾ (dựa trên soát repo)

### Đã hoàn thành / đang tốt
- Adapter Pattern đầy đủ 6 interface, code sạch, đúng docstring chuẩn
- Evaluate Gate dùng LLM-as-judge (không chỉ threshold đơn giản) — điểm cộng lớn khi bảo vệ
- Golden Path #1 có Argo Workflows template thật
- LLMOps active scope (Vector DB, LLM Gateway, Prompt Registry) — đúng vì đã xác nhận nhu cầu thật

### CẢNH BÁO — 3 điểm cần tự kiểm tra ngay

1. **3 MCP server đã tồn tại (mlops/k8s/metrics), vượt khuyến nghị "1 proof-of-concept"** — mục 4.5 (bản trước) khuyến nghị chỉ 1 MCP tool nhẹ ở tuần cuối. Cần tự hỏi: có đang dành quá nhiều thời gian cho phần Agent-ready thay vì củng cố Golden Path #2 (phần lõi, quan trọng nhất theo ma trận ưu tiên) chưa?
   → **Hành động**: kiểm tra Golden Path #2 (Register→Deploy) đã chạy end-to-end demo được chưa. Nếu CHƯA, tạm dừng mở rộng MCP, dồn lực hoàn thiện Golden Path #2 trước.

2. **Evaluate Gate (`evaluations/gate.py`) mới chấm safety/correctness/relevance theo rubric, chưa có test đối kháng (adversarial/red-team)** — theo chương 13 sách *Machine Learning Platform Engineering*, đây là bước bắt buộc trước khi gắn nhãn "Production" cho 1 phiên bản model/prompt. Vì Gate là lõi của Golden Path #2 (ưu tiên số 1), đây là việc CỦNG CỐ lõi, không phải mở rộng phạm vi mới — nên làm trước phần LLMOps khác (caching, guardrails...).
   → **Hành động**: thêm một bộ prompt jailbreak nhỏ (5-10 câu tấn công mẫu) vào `gate.py`, chạy trước khi cho phép chuyển trạng thái "Production".

3. **`infra/opa-policies/`, `infra/helm-charts/`, `infra/argocd/` mới chỉ có README** ("week 8+") — đây là phần thực thi Golden Path #2 thật. **Đã chốt (mục 9): Cường tự phát triển GitOps sync (ArgoCD+Helm cho KServe) trước, không chờ netCI** — rủi ro phụ thuộc Hiếu ở hạng mục này đã được loại bỏ; việc còn lại thuần là effort tự làm, không phải rủi ro lịch trình người khác.

### Scope chốt lại

| # | Hạng mục | Vai trò | Trạng thái |
|---|---|---|---|
| 1 | Golden Path #1 (Train→Track→Register, Argo Workflows) | Lõi | Có nền, cần hoàn thiện |
| 2 | Golden Path #2 (Register→Deploy, Evaluate Gate → ArgoCD/Helm hoặc netCI) | **Lõi — ưu tiên số 1 hiện tại** | Chưa hoàn thiện (infra/* mới README) |
| 3 | LLMOps active (Vector DB, LLM Gateway, Prompt Registry) | Lõi mở rộng, đã xác nhận nhu cầu thật | Có nền tảng adapter |
| 4 | MCP + Skills | Stretch — ĐANG VƯỢT SCOPE, cần rà soát | 3 server đã có, cân nhắc rút gọn còn 1 |
| 5 | `netci_adapter.py` (mock) | Chuẩn bị sẵn sàng gọi Hiếu | **CẦN LÀM NGAY — còn thiếu file này** |

---

## 8. RANH GIỚI VỚI HIẾU — REPO, API CONTRACT, RỦI RO PHỤ THUỘC

### Repo: TÁCH RIÊNG, không chung monorepo

| Lý do | Giải thích |
|---|---|
| Chấm điểm độc lập | 2 người bảo vệ 2 đồ án riêng, cần git history tách bạch |
| Stack khác nhau | netCI: Groovy/Ansible/Helm là chính; AI Delivery Portal: Python/TypeScript |
| Đúng Adapter Pattern | Gọi qua API buộc ranh giới rõ ràng, tránh "tiện thì import thẳng code nội bộ" |

### Cách giao tiếp — API Contract nhẹ (không cần repo thứ 3 nếu thấy cồng kềnh)
- Thống nhất OpenAPI spec hoặc chí ít danh sách endpoint + request/response mẫu cho: `trigger_job`, `get_job_status`, `get_console_log_stream`.
- Mỗi bên tự giữ bản mô tả kỳ vọng trong repo của mình, review chéo định kỳ.

### Rủi ro phụ thuộc — cách xử lý
- **`netci_adapter.py` PHẢI ở dạng mock hoàn chỉnh cho tới khi Hiếu có API thật** — tuyệt đối không để tiến độ Golden Path #2 phụ thuộc vào tiến độ netCI (Hiếu có khối lượng SRE nặng: multi-cluster, SBOM, ký artifact — rủi ro chậm cao hơn).
- Đây chính là lý do Adapter Pattern được chọn từ đầu — không phải chỉ cho MLflow/KServe, mà cho CẢ hệ thống anh em (netCI) cũng áp dụng cùng nguyên tắc.

### Điều kiện để hỗ trợ Hiếu (nếu dư thời gian) — 3 điều kiện, đủ CẢ 3 mới hành động
1. Golden Path #1 + #2 của MÌNH đã chạy ổn định, demo/benchmark được.
2. Có quỹ thời gian dư THỰC SỰ (nhiều tuần, không phải vài buổi rảnh).
3. Hiếu XÁC NHẬN cần hỗ trợ — không tự đoán.

Nếu đủ điều kiện: chỉ hỗ trợ đúng **điểm giao thoa** (API contract, làm early-tester cho API của Hiếu) — KHÔNG học lại toàn bộ mảng SRE sâu (multi-cluster ops, SBOM) vì không tương xứng effort/lợi ích.

---

## 9. CÂU HỎI CÒN MỞ — CẦN HỎI HIẾU/MENTOR SỚM

- [x] Cơ chế GitOps sync (ArgoCD+Helm) cho việc deploy MODEL lên KServe — **CHỐT: Cường tự phát triển trước** (vì có yêu cầu đặc thù: Canary theo accuracy, không chỉ health check generic), sau đó mới tích hợp/bàn giao chung vào netCI Delivery Platform khi cả 2 bên sẵn sàng.
- [ ] OPA (resource limit, security scan generic) — netCI có cung cấp sẵn không, hay Cường tự làm nhẹ riêng cho scope của mình?
- [ ] netCI có endpoint nào để lấy console log stream nhúng vào Portal không (đúng yêu cầu UX "không rời khỏi Portal")?
- [ ] Nếu Golden Path #2 cần "chờ Approve lâu" (durable wait) — netCI/Jenkins có cơ chế nào hỗ trợ, hay đây là bài toán Cường tự xử lý ở tầng Orchestration API riêng (không cần Temporal, có thể chỉ cần lưu trạng thái "pending approval" vào DB + webhook)?

---

## 10. CHECKLIST HỎI MENTOR (còn hiệu lực, bổ sung ở mục 9)

- [x] AI Platform hiện tại dùng nền tảng gì — ĐÃ XÁC NHẬN có Qwen serving, fine-tune, cost tracking
- [ ] Team hiện mất trung bình bao lâu để deploy 1 model? (số liệu vàng cho slide vấn đề — vẫn cần lấy)
- [ ] Có từng xảy ra sự cố do thiếu chuẩn hóa/thiếu healthcheck không?
- [ ] Có quy trình rollback rõ ràng chưa?
- [ ] Có được cấp cluster lab riêng để dev/test không?

---

## 11. BỐ CỤC SLIDE BẢO VỆ — CẬP NHẬT KHUNG 2 SẢN PHẨM

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
15. Roadmap Production — bao gồm Crossplane/Temporal/Kusion như hướng tương lai (không phải hiện tại)
16. Kết luận
```

---

## 12. CÂU TRẢ LỜI MẪU CHO CÂU HỎI KHÓ

**Q: "Sao không tự làm Jenkins/CI-CD, lại đi gọi qua netCI của người khác?"**
> "Việc chuẩn hóa CI/CD generic (multi-cluster Jenkins, ephemeral agent, SBOM) là bài toán hạ tầng tổng quát — Adapter Pattern của em cho phép tách biệt rõ: em tập trung vào NGHIỆP VỤ đặc thù MLOps (Evaluate Gate, Drift→Retrain) là nơi tạo giá trị khác biệt, còn cơ chế thực thi generic thì tái sử dụng, tránh trùng lặp công sức với đề tài netCI đang chạy song song."

**Q: "Nếu netCI của Hiếu chưa xong, Portal của em có chạy được không?"**
> "Có — `netci_adapter.py` được thiết kế mock hoàn chỉnh ngay từ đầu, đúng nguyên tắc Adapter Pattern đã áp dụng cho mọi hệ thống con khác. Golden Path của em không phụ thuộc tiến độ netCI để phát triển và demo."

**Q: "Golden path của em dừng ở Deploy, model xuống cấp thì sao?"**
> "Em đã có `agents/skills/evaluate_drift.py` làm nền cho vòng lặp Retrain — phần trigger tự động nằm trong roadmap, nhưng cơ chế phát hiện drift đã có sẵn."

**Q: "Sao lại thêm MCP/Agent, đề bài đâu có yêu cầu?"**
> "Orchestration API thiết kế theo Facade Pattern — thêm kênh truy cập cho AI Agent gần như không phát sinh rủi ro kiến trúc. Đây là minh chứng cho việc thiết kế Adapter/Facade từ đầu là đúng đắn, đón đầu xu hướng Agentic Platform Engineering."

---

## 13. TÀI LIỆU HỌC — GIỮ NGUYÊN, BỔ SUNG

- MLOps Zoomcamp, Made With ML, Full Stack Deep Learning (LLMOps module) — như bản trước
- *Introducing MLOps*, *Practical MLOps*, *Building Machine Learning Pipelines*
- `mlflow.org/docs`, `kserve.github.io`, `backstage.io/docs`
- MCP specification (`modelcontextprotocol.io`) — đọc kỹ hơn vì đã có 3 server thật trong repo, cần đảm bảo đúng chuẩn
- **MỚI**: Đọc kỹ tài liệu bàn giao/API của netCI khi Hiếu có bản đầu tiên — ưu tiên hơn đọc thêm về Temporal/Kusion (đã hạ cấp khỏi scope)

---

## 14. NGUYÊN TẮC GHI NHỚ TỔNG QUÁT

1. Luôn quay lại **5 câu hỏi cốt lõi** (mục 0, đã thêm câu hỏi ranh giới với netCI)
2. Chiều sâu > chiều rộng — **Golden Path #2 là ưu tiên số 1 hiện tại**, không mở rộng MCP thêm cho tới khi #2 xong
3. Mọi thiết kế phải có lý do — kể cả lý do KHÔNG dùng 1 công nghệ (Temporal/Kusion/Crossplane) cũng cần ghi lại, không chỉ lý do có dùng
4. Chủ động nêu giới hạn — đặc biệt phần đang mock chờ netCI
5. Số liệu thật từ Viettel > giả định — đã có 1 phần (Qwen), còn thiếu số liệu thời gian deploy
6. **Adapter Pattern là bảo hiểm — áp dụng cho CẢ hệ thống anh em (netCI), không chỉ hệ thống AI Platform**
7. Nghĩ như Platform Engineer thật — golden path giải quyết pain point thật, đo lường được, có đường tới production
8. Agent-ready là triết lý thiết kế, nhưng **không được lấn át việc hoàn thiện Golden Path lõi** — 3 MCP server hiện tại là tín hiệu cần tự kiểm tra lại ưu tiên
9. **MỚI — Ranh giới rõ với đội nhóm**: trước khi code bất kỳ tính năng "nghe hay" nào, hỏi câu lọc #5 (mục 0) — đây là nghiệp vụ của mình hay hạ tầng tổng quát của người khác?
10. **MỚI — Chỉ giúp đồng đội khi đủ 3 điều kiện** (mục 8) — đừng để tinh thần nhiệt tình phá vỡ kỷ luật scope của chính mình

---

*Cập nhật lần 3, sau khi: (a) mentor phân Phase rõ ràng giữa Cường (GitOps for Model) và Hiếu (netCI); (b) soát trực tiếp repo thật `AI-delivery-portal`. Review tiếp theo nên làm ngay sau khi: Golden Path #2 chạy end-to-end lần đầu, VÀ sau buổi thống nhất API contract với Hiếu.*