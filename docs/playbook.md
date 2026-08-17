# SỔ TAY THAM CHIẾU
## AI Delivery Portal — Internal Developer Platform cho MLOps/LLMOps
### Viettel Digital Talent 2026 · Track Cloud · Phase 2

---

## 0. LA BÀN — 3 CÂU HỎI CỐT LÕI DÙNG XUYÊN SUỐT HÀNH TRÌNH

Mỗi khi phân vân "có nên làm tính năng này không", "có nên ưu tiên việc này không" — quay lại 3 câu hỏi này:

1. **Việc gì lặp lại thường xuyên nhất?** (Frequency) — càng lặp lại nhiều, tự động hóa càng có ROI cao.
2. **Việc gì dễ sai nhất?** (Error-proneness) — càng dễ sai do thao tác thủ công, càng cần policy/template chặn trước.
3. **Việc gì có rủi ro cao nhất nếu làm sai?** (Impact/Blast radius) — càng ảnh hưởng lớn (production, nhiều team), càng cần gate kiểm soát chặt.

### Ma trận ưu tiên (dùng cho mọi quyết định thiết kế)

```
                    Rủi ro thấp              Rủi ro cao
Tần suất cao   │  Tự động hóa nhẹ nhàng  │  ƯU TIÊN SỐ 1
               │  (VD: log experiment)    │  (VD: deploy production)
───────────────┼──────────────────────────┼───────────────────────────
Tần suất thấp  │  Ưu tiên thấp nhất       │  Stretch goal, đáng làm
               │  (VD: setup notebook)     │  nếu còn thời gian
               │                           │  (VD: rollback)
```

**Nguyên tắc**: luôn ưu tiên ô "Tần suất cao × Rủi ro cao" trước — đây là nơi golden path tạo giá trị lớn nhất và dễ đo lường (benchmark) nhất.

---

## 1. ĐỊNH VỊ ĐỀ TÀI — CÂU CHUYỆN CỐT LÕI

> *"AI Platform của Viettel đã có đủ năng lực mạnh (Registry, Experiment, Inference, Notebook), nhưng thiếu một lớp kết nối chuẩn hóa. Portal không thay thế các hệ thống này — nó là lớp DevEx/orchestration nằm trên, biến quy trình rời rạc, thủ công, dễ sai thành golden path tự động, an toàn, đo lường được."*

### Vì sao đề tài này "hay" hơn cảm giác ban đầu

- Đây không phải "làm CI/CD portal" thuần túy — đây là **Platform Engineering áp dụng vào domain MLOps**, một lĩnh vực đang rất hot trong ngành.
- Giá trị thực tế cao: đúng cái leader cần → nếu làm tốt, sản phẩm có khả năng dùng thật, không nằm trong ngăn kéo sau khi bảo vệ.
- Có đủ chiều sâu kỹ thuật nếu biết khai thác đúng: design pattern, kiến trúc adapter, policy-as-code, domain knowledge MLOps/LLMOps.

### Cấu trúc kiến thức core (4 trụ cột, không phải 2)

```
1. Software Engineering       → nền tảng (design pattern, API design)
2. Platform Engineering/DevOps → THÂN BÀI CHÍNH (IDP, Golden Path, K8s, GitOps)
3. DevSecOps                  → một khía cạnh trong đó (policy-as-code, OPA)
4. MLOps/LLMOps domain        → phần làm đề tài KHÁC BIỆT, không thể bỏ qua
```

---

## 2. GOLDEN PATH — KHÁI NIỆM NỀN TẢNG

### Định nghĩa

> **Golden Path = con đường được trải sẵn, dễ đi nhất, đã chuẩn hóa best-practice, để hoàn thành một công việc lặp lại — giúp "làm đúng" trở thành lựa chọn dễ dàng nhất, không cần ép buộc.**

### Vị trí trong bức tranh lớn

```
Internal Developer Platform (IDP)   ← triết lý/mục tiêu ("dev tự phục vụ")
        └── Golden Path             ← cách hiện thực hóa (con đường chuẩn)
                └── Backstage        ← công cụ cụ thể để build
```

### 6 nguyên tắc nền tảng (universal, áp dụng mọi công ty)

1. **"Paved road, not the only road"** — khuyến nghị, không ép buộc tuyệt đối.
2. **Giảm cognitive load** — hệ thống "nhớ hộ" best-practice, dev không cần nhớ hết.
3. **Self-service** — dev tự làm được ngay, không chờ người khác.
4. **Bắt đầu từ pain point thật** — không phải từ "có công cụ hay nên nhét vào".
5. **Đo lường được** — có metric: adoption rate, thời gian, số lỗi giảm.
6. **Là sản phẩm sống** — cần bảo trì, cập nhật định kỳ, không làm 1 lần rồi bỏ.

### Điều khác nhau giữa các công ty (không có 1 khuôn mẫu chung)

| Yếu tố | Ảnh hưởng đến thiết kế Golden Path |
|---|---|
| Hạ tầng sẵn có | Golden path phải neo vào hạ tầng thật, không copy nguyên mẫu công ty khác |
| Quy mô/độ trưởng thành | Tổ chức lớn (như Viettel) → nhiều gate/governance hơn |
| Văn hóa | Viettel (viễn thông, cần ổn định) → ưu tiên an toàn hơn tốc độ tuyệt đối |
| Loại workload | MLOps có đặc thù riêng khác DevOps thường (xem mục 3) |

**→ Với Viettel**: golden path nên có policy gate rõ ràng, audit trail đầy đủ, và **để lối thoát** cho trường hợp đặc biệt (không ép buộc 100% qua Portal).

---

## 3. VÒNG ĐỜI MODEL — ẢNH HƯỞNG TRỰC TIẾP ĐẾN THIẾT KẾ

```
Train → Experiment → Evaluate → Register → Deploy → Monitor → Retrain ─┐
  ↑                                                                      │
  └──────────────────────────────────────────────────────────────────┘
        (vòng lặp, KHÔNG phải đường thẳng như CI/CD thường)
```

### Bảng ánh xạ: Domain Knowledge → Quyết định thiết kế

| Domain Knowledge | Golden Path bị ảnh hưởng | Thay đổi thiết kế cụ thể |
|---|---|---|
| Model versioning ≠ Code versioning | #1 Register | Metadata cần: `git_commit_hash` + `dataset_version` + `hyperparameters`, không chỉ file model |
| Data lineage | #1 Register | Thêm field `data_source_uri`, `data_snapshot_id` |
| Evaluate là gate ẩn (không nằm trong 4 hệ thống đề bài liệt kê) | Giữa #1 và Register | Đây là insight tự phát hiện — nhấn mạnh khi bảo vệ |
| Model drift | #2 Deploy → Monitor | Dashboard cần metric distribution/drift, không chỉ uptime |
| A/B testing model | #2 Deploy | Hỗ trợ Canary/Shadow deploy, không chỉ Blue-Green đơn giản |
| Prompt versioning (LLMOps) | Mở rộng Registry | Prompt Registry tách biệt Model Registry |
| RAG (LLMOps) | Kiến trúc tổng thể | Thêm Vector DB nếu đào sâu LLM |
| Đánh giá văn bản LLM | Gate Evaluate | Cần LLM-as-judge, không dùng threshold đơn giản như accuracy |

### Câu trả lời mẫu khi bị hỏi "Golden path của em khác gì CI/CD thường?"

> *"CI/CD thông thường tuyến tính, phục vụ code. Golden path MLOps phải mô hình hóa đúng bản chất chu kỳ và các gate đặc thù — đặc biệt là Evaluate (kiểm tra chất lượng model trước khi promote) và Retrain (đóng vòng lặp khi model xuống cấp) — những khái niệm không tồn tại trong CI/CD phần mềm thông thường."*

---

## 4. KIẾN TRÚC HỆ THỐNG

```
┌────────────────────────────────────────────┐
│         Portal UI (Backstage)                 │
├────────────────────────────────────────────┤
│   BFF / Orchestration API (FastAPI)            │
│   - Auth (Keycloak) - Golden Path Engine        │
│   - Workflow trigger (Argo Workflows)           │
├───┬────────┬────────┬────────┬────────────┤
│Registry│Experiment│Inference│Notebook│      Adapter Layer
│Adapter │ Adapter  │ Adapter │Adapter │      (interface chung)
├───┴────────┴────────┴────────┴────────────┤
│ MLflow │ MLflow   │ KServe/ │Kubeflow│      Backend thật/mock
│Registry│ Tracking │BentoML  │Notebook│      (đổi được không sửa Portal)
└────────────────────────────────────────────┘
   Cross-cutting: OPA (policy) | Prometheus/Grafana (observability)
                  | ArgoCD + Helm (GitOps CD)
```

### Nguyên tắc thiết kế quan trọng nhất

**Adapter Pattern là xương sống**: mỗi hệ thống con qua 1 interface chung → mock trước, cắm hệ thống thật sau, không sửa lại Portal.

```python
class IModelRegistryAdapter(ABC):
    def register_model(self, name, version, artifact_uri) -> ModelInfo: ...
    def list_models(self, project) -> List[ModelInfo]: ...

class MLflowRegistryAdapter(IModelRegistryAdapter): ...   # mock/thật nếu Viettel dùng MLflow
class ViettelRegistryAdapter(IModelRegistryAdapter): ...  # viết thêm khi có info thật
```

---

## 5. TECH STACK — SOÁT LẠI THEO GOVERNANCE (tránh nói sai khi bị hỏi)

| Layer | Công nghệ | Thuộc quỹ nào |
|---|---|---|
| Portal UI | **Backstage** | ✅ CNCF Graduated |
| Orchestration API | FastAPI (Python) | Độc lập |
| Golden path template | Backstage Software Templates | (thuộc Backstage) |
| Auth | Keycloak | Độc lập (Red Hat), không CNCF |
| Model Registry + Experiment | **MLflow** | LF AI & Data Foundation (KHÔNG phải CNCF) |
| Inference | **KServe** (hoặc BentoML nhẹ hơn) | LF AI & Data Foundation |
| Notebook | Kubeflow Notebooks / JupyterHub | LF AI & Data / độc lập |
| CI | GitLab CI | Độc lập |
| CD/GitOps | **ArgoCD** | ✅ CNCF Graduated |
| Packaging | **Helm** | ✅ CNCF Graduated |
| Policy | **OPA** | ✅ CNCF Graduated |
| Observability | Prometheus (✅ CNCF) + Grafana/Loki (❌ không CNCF, Grafana Labs) | Hỗn hợp |

**Câu nói chuẩn khi trình bày**: *"Ưu tiên các dự án CNCF cho lớp hạ tầng/nền tảng (Backstage, ArgoCD, Helm, OPA, Prometheus), kết hợp dự án chuẩn ngành MLOps thuộc LF AI & Data Foundation (MLflow, Kubeflow, KServe) — toàn bộ stack đều open-source, tránh vendor lock-in."*

### Ngôn ngữ sử dụng

| Ngôn ngữ | Dùng ở đâu |
|---|---|
| Python | Backend/API, Adapter, script benchmark |
| TypeScript/React | Backstage custom plugin |
| YAML | K8s manifest, Helm, Argo Workflow, Backstage Template |
| Rego | Viết OPA policy rule (học riêng 1-2 ngày) |
| Bash | Script tiện ích |

---

## 6. DESIGN PATTERN — BỘ 4 NÊN DÙNG (không nhồi nhét cả 8)

| Pattern | Áp dụng ở đâu | Vì sao "đắt giá" để nói khi bảo vệ |
|---|---|---|
| **Adapter** | Kết nối MLflow/KServe/hệ thống thật | Cốt lõi — cho phép đổi backend không sửa Portal |
| **Template Method** | Định nghĩa khung Golden Path chuẩn, cho override từng bước | Khớp CHÍNH XÁC bản chất "con đường chuẩn nhưng tùy biến được" của Golden Path |
| **Chain of Responsibility** | Chuỗi policy check (OPA): resource limit → security scan → evaluation-passed | Khớp với cơ chế enforce nhiều điều kiện tuần tự |
| **Factory** | Chọn đúng Adapter theo config | Đi kèm tự nhiên với Adapter, dễ mở rộng |

*(Facade, Strategy, Observer, Builder là pattern phụ — biết để dùng đúng chỗ, không bắt buộc liệt kê hết khi bảo vệ)*

---

## 7. SCOPE — GOLDEN PATH NÊN LÀM BAO NHIÊU

### Quyết định: 2 golden path lõi + 1 stretch goal

| # | Golden Path | Vai trò | Đầu tư |
|---|---|---|---|
| 1 | **Train → Track → Register** | Chuẩn hóa đầu vào, giải quyết "tần suất cao" | Vừa phải |
| 2 | **Register → Deploy** | Giải quyết cả "dễ sai nhất" + "rủi ro cao nhất" | **Sâu nhất — trọng tâm** |
| 3 (stretch) | Rollback/Promote version | Đóng góp thêm cho #2, không cần làm riêng | Nếu dư thời gian (tuần 10-11) |

**Lý do không làm nhiều hơn**: Claude Code giúp code nhanh hơn, nhưng KHÔNG rút ngắn được thời gian thiết kế, tích hợp thật, test, và benchmark — đây là bottleneck thật sự, không phải viết code.

**Notebook**: chỉ tích hợp mức tối thiểu (link redirect), KHÔNG cần thành golden path riêng — giá trị thấp hơn nhiều so với 2 cái trên.

---

## 8. LỘ TRÌNH 12 TUẦN

| Tuần | Nội dung |
|---|---|
| 1 | Hỏi mentor (xem checklist mục 10). Đọc khái niệm Golden Path/IDP/Backstage TRƯỚC khi code. Test-drive Backstage cơ bản |
| 2-3 | Setup lab: MLflow, fake GPU/mock inference, viết Adapter interface + Mock Adapter |
| 4-5 | Viết Adapter thật nếu được cấp quyền; song song viết BFF API (FastAPI) |
| 6-7 | Golden Path #1: Train → Track → Register (Argo Workflows) |
| 8-9 | Golden Path #2: Register → Deploy (Helm template + ArgoCD + OPA policy) |
| 10 | Dashboard observability, bắt đầu benchmark; stretch: Rollback |
| 11 | Hoàn thiện báo cáo, slide, quay video demo backup, viết roadmap production |
| 12 | Thuyết trình thử với mentor, chỉnh sửa, chuẩn bị Q&A |

---

## 9. BENCHMARK — CÁCH CHỨNG MINH GIÁ TRỊ BẰNG SỐ LIỆU

### Nguyên tắc chung
1. Có baseline rõ ràng (thủ công / default).
2. Cùng điều kiện đo.
3. Ít nhất 3 loại chỉ số: hiệu quả, tiết kiệm, trải nghiệm.
4. Biểu đồ trực quan, không chỉ bảng số.

### Bộ benchmark cho Portal (tự đo được, không cần chờ user thật)

| Cách đo | Ví dụ số liệu |
|---|---|
| Thao tác thủ công vs qua Portal (tự đo lặp lại nhiều lần) | "Deploy thủ công 25 phút/12 bước → qua Portal 3 phút/2 bước, giảm 88%" |
| Fault injection (cố tình tạo lỗi cấu hình phổ biến) | "20 kịch bản lỗi: thủ công lọt 14/20 ra production; qua golden path chặn 18/20" |
| Standardization coverage | "70% điểm chạm thủ công được loại bỏ nhờ golden path" |
| A/B nhỏ với đồng nghiệp (nếu có thể) | Thời gian hoàn thành trung bình, mẫu nhỏ vẫn có giá trị ở mức thực tập |
| Hiệu năng hệ thống | Latency API, throughput orchestration layer |

**Lưu ý khi trình bày**: nhấn mạnh "đo nhiều lần, nhiều kịch bản" thay vì cố nói "quy mô lớn" — mẫu nhỏ vẫn thuyết phục nếu lặp lại có kiểm soát.

---

## 10. CHECKLIST CÂU HỎI HỎI MENTOR (làm ngay tuần 1)

- [ ] AI Platform hiện tại dùng nền tảng gì — tự build hay MLflow/Kubeflow/Seldon?
- [ ] Inference đang serving bằng gì — KServe, Seldon, Triton, hay custom?
- [ ] Có API/SDK nội bộ để Portal gọi vào không? Có được cấp service account không?
- [ ] Auth hiện tại dùng gì (SSO/LDAP/Keycloak)?
- [ ] Team hiện mất trung bình bao lâu để deploy 1 model? (→ số liệu vàng cho slide vấn đề)
- [ ] Có từng xảy ra sự cố do thiếu chuẩn hóa/thiếu healthcheck không?
- [ ] Có quy trình rollback rõ ràng chưa, hay đang xử lý thủ công?
- [ ] Có được cấp cluster lab riêng để dev/test không?
- [ ] Viettel có đang có nhu cầu LLM/chatbot nội bộ thật không? (quyết định có đào sâu LLMOps hay không)

**Nguyên tắc**: nếu lấy được dù chỉ 1-2 con số/câu chuyện thật, gap sẽ không còn là giả định — mà là vấn đề đã được xác nhận bởi người trong cuộc. Đây là khác biệt giữa bài bảo vệ "nghe hợp lý" và "thuyết phục thật sự".

---

## 11. BỐ CỤC SLIDE BẢO VỆ (15-18 slide)

```
Phần 1 — Mở đầu & Vấn đề (3 slide)
  1. Trang bìa
  2. Bối cảnh AI Platform hiện tại
  3. ⭐ Vấn đề thật (pain point có số liệu) — SLIDE QUAN TRỌNG NHẤT

Phần 2 — Giải pháp & Kiến trúc (5-6 slide)
  4. Giải pháp tổng quan (before/after)
  5. Kiến trúc hệ thống
  6. Technology Justification (CNCF/LF AI & Data)
  7. Golden Path #1
  8. Golden Path #2 (trọng tâm)
  9. Adapter Pattern / khả năng mở rộng

Phần 3 — Demo & Kết quả (4-5 slide)
  10. Demo (live + video backup)
  11. Benchmark thời gian/số bước
  12. Benchmark số lỗi bị chặn
  13. Dashboard observability

Phần 4 — Đánh giá (2 slide)
  14. Giới hạn hiện tại (chủ động nêu, thể hiện trung thực)
  15. Bài học kinh nghiệm

Phần 5 — Tầm nhìn (2 slide)
  16. ⭐ Roadmap đưa vào Production — SLIDE QUAN TRỌNG THỨ 2
  17. Kết luận
```

**2 slide quyết định "vượt trội"**: Slide 3 (Vấn đề thật) và Slide 16 (Roadmap production) — đây là 2 chỗ thể hiện tư duy thực tế/kinh doanh, không chỉ kỹ thuật thuần túy, chính là thứ giúp bạn nổi bật để lên full-time.

---

## 12. CÂU TRẢ LỜI MẪU CHO CÂU HỎI KHÓ

**Q: "Sao không dùng Backstage/MLflow/Kueue có sẵn cho xong, tự làm gì?"**
> "Em không viết lại các hệ thống này — Portal là lớp DevEx/orchestration nằm trên, dùng đúng các dự án CNCF/LF AI & Data đã kiểm chứng ở production quy mô lớn. Giá trị của em nằm ở việc thiết kế golden path đúng đặc thù MLOps của Viettel, tích hợp chúng lại thành 1 luồng chuẩn hóa, có policy enforcement và benchmark chứng minh hiệu quả — điều mà việc dùng riêng lẻ từng công cụ không tự có được."

**Q: "Golden path của em dừng ở Deploy, model xuống cấp thì sao?"**
> "Em đã thiết kế Monitor dashboard làm nền cho vòng lặp Retrain — do giới hạn 3 tháng, phần trigger tự động retrain nằm trong roadmap đề xuất (slide 16), nhưng kiến trúc hiện tại đã sẵn sàng mở rộng vì Adapter pattern cho phép cắm thêm bước mà không phá vỡ thiết kế."

**Q: "Có đo được benchmark khách quan không, mẫu nhỏ liệu có tin cậy?"**
> "Em benchmark theo 2 cách: (1) tự đo lặp lại nhiều lần cùng 1 kịch bản (thủ công vs qua Portal) để có độ tin cậy qua số lần lặp, (2) fault-injection với kịch bản lỗi kiểm soát được — cả 2 đều không phụ thuộc số lượng user thật, phù hợp với thời gian 3 tháng."

---

## 13. TÀI LIỆU HỌC — DANH SÁCH ĐÃ LỌC (không cần đọc hết, chọn theo giai đoạn)

### Khóa học (ưu tiên, thực hành nhiều)
- **MLOps Zoomcamp** (DataTalks.Club) — free, 3 tháng, dùng đúng stack MLflow/Docker/Prometheus/Grafana/GitHub Actions — sát nhất với đề tài.
- **Made With ML** — free, dạy xây hệ thống ML end-to-end (tracking, testing, serving, monitoring).
- **Full Stack Deep Learning — LLM Bootcamp** — module "LLMOps: Deployment and Learning in Production", dùng nếu đào sâu LLMOps.

### Sách
- *Introducing MLOps* (Mark Treveil & Dataiku Team) — nhập môn, bối cảnh doanh nghiệp (khớp với Viettel).
- *Practical MLOps* — thực hành CI/CD cho ML, hạ tầng, monitoring.
- *Building Machine Learning Pipelines* (Hapke & Nelson) — sâu về pipeline/orchestration.

### Documentation kỹ thuật
- `mlflow.org/docs` — đọc kỹ "Model Registry" + "Tracking" trước khi viết Adapter.
- `kserve.github.io/website` — khái niệm "InferenceService".
- `backstage.io/docs/overview/what-is-backstage` — đọc "Concepts" trước khi code.
- Bài blog gốc **"Golden Paths" — Spotify Engineering** (đọc bản gốc, nơi khái niệm ra đời).
- `platformengineering.org` — định nghĩa & case study Platform Engineering.

### Academic papers (trích dẫn cho phần Related Work, không cần implement)
- *Themis: Fair and Efficient GPU Cluster Scheduling* (NSDI 2020) — nếu muốn liên hệ chéo sang fairness.
- (Chủ yếu tham khảo về mặt tư duy hệ thống MLOps quy mô lớn — không bắt buộc với đề tài Portal, ưu tiên hơn cho phía Scheduler nếu có liên quan)

---

## 14. NGUYÊN TẮC GHI NHỚ TỔNG QUÁT (áp dụng mọi quyết định trong 3 tháng)

1. **Luôn quay lại 3 câu hỏi cốt lõi** (mục 0) khi phân vân làm gì trước.
2. **Chiều sâu > chiều rộng** — 2 golden path làm kỹ hơn 4 golden path làm hời hợt.
3. **Mọi thiết kế phải có lý do**, không chọn công nghệ/pattern "vì thấy hay" — luôn trả lời được "tại sao chọn cái này".
4. **Chủ động nêu giới hạn** thay vì để giám khảo tự phát hiện — thể hiện sự trung thực, chuyên nghiệp.
5. **Số liệu thật từ Viettel > số liệu giả định** — dành thời gian hỏi mentor sớm nhất có thể.
6. **Adapter Pattern là bảo hiểm** — thiết kế sẵn sàng chuyển từ mock sang thật mà không phải viết lại.
7. **Đừng chỉ làm đồ án — nghĩ như một Platform Engineer thật**: golden path phải giải quyết pain point thật, đo lường được, và có đường đi tới production.

---

*Sổ tay này nên được review lại vào cuối mỗi giai đoạn lớn (sau tuần 3, tuần 7, tuần 10) để điều chỉnh theo thực tế phát sinh trong quá trình làm việc với mentor và hệ thống thật của Viettel.*