# LLMOps Lifecycle — Draft Plan

> **Trạng thái: DRAFT** — ghi lại từ phiên thảo luận sau khi hoàn thiện MLOps
> Golden Path #1/#2. Chưa triển khai, chưa chốt các câu hỏi mở ở cuối file.
> Tác giả sẽ tự verify kỹ phần MLOps trước khi quay lại chốt file này.

## 1. Bối cảnh

`docs/playbook-ai-delivery-portal.md` xác định "Đối tượng thứ nhất" của đề tài
là luồng **MLOps/LLMOps** cho các sản phẩm AI Platform. Phần MLOps (Golden Path
#1 Train→Track→Register, #2 Register→Deploy) đã hoàn thiện end-to-end (train
thật qua Argo Workflows trên kind cluster, Evaluate Gate thật, PR deploy thật,
Dashboard hiển thị kết quả). Phần LLMOps — vốn được playbook liệt kê gồm 3 trụ
cột "Vector DB + LLM Gateway + Prompt Registry" — mới có từng mảnh rời rạc,
chưa nối thành 1 luồng end-to-end.

## 2. LLMOps khác MLOps ở điểm nào

| | MLOps | LLMOps |
|---|---|---|
| Đối tượng quản lý | Model tự train (weights mới) | LLM có sẵn (Claude/Qwen...) — không tự train, chỉ dùng lại qua API |
| "Version" nghĩa là gì | Model artifact mới sau khi train | Prompt mới, hoặc tập tài liệu RAG mới — trọng số LLM không đổi |
| Đánh giá chất lượng | Metric số (accuracy/precision/recall) so ngưỡng | Chủ yếu LLM-as-judge (output là văn bản tự do) |
| "Deploy" nghĩa là gì | Đưa model lên serving endpoint (KServe) | Kích hoạt prompt/RAG version làm "đang sống" cho endpoint chat |
| Vòng lặp giám sát | Data drift → Monitor→Drift→Retrain | Phản hồi người dùng / re-run eval set định kỳ, không phải "retrain" |

## 3. Pain point có giống 2 Golden Path của MLOps không?

**Giống về hình dạng** — lý do 2 Golden Path tồn tại vẫn đúng cho LLMOps:
- **Golden Path #1 tương ứng** (Track→Register): prompt/tài liệu RAG mới cần
  version + lineage trước khi ai tin dùng — tần suất thay đổi prompt trong
  thực tế còn cao hơn tần suất train lại model.
- **Golden Path #2 tương ứng** (Register→Deploy + Evaluate Gate): pain point
  cấp thiết nhất của LLMOps thực tế — sửa prompt xong đẩy thẳng production,
  không ai review, không có "build step" nào bắt lỗi.

**Khác về cơ chế vận hành phía sau — không nên copy y nguyên:**
- "Track" không nặng như "Train": sửa prompt không cần cả Argo Workflow chạy
  job dài; chỉ RAG ingest quy mô lớn mới cần kiểu batch-job giống Argo.
- "Deploy" nhẹ hơn nhiều: đổi prompt/RAG version active gần như là đổi 1 con
  trỏ config, giống bật/tắt feature flag hơn là "provision hạ tầng" — nếu vẫn
  bắt đi qua PR + chờ merge như MLOps Golden Path #2 có thể tạo ma sát không
  cần thiết cho pain point cần phản hồi nhanh.

## 4. Quyết định đã chốt trong phiên thảo luận

**Không đưa fine-tune LLM thật (LoRA/Qwen qua Ollama...) vào LLMOps lifecycle
đợt này.** `infra/argo-workflows/fine-tune-template.yaml` (`fine-tune-golden-path`)
giữ nguyên như một phần của MLOps Golden Path #1 — nó vận hành trên model cổ
điển (LogisticRegression demo), không phải LLM thật, nên về bản chất kỹ thuật
nó đã đúng chỗ.

Lý do:
- Best practice ngành LLMOps đi theo thứ tự: **Prompting → RAG → Fine-tuning**
  (fine-tuning là lựa chọn cuối cùng khi 2 bước trước không đủ, không phải
  điểm khởi đầu). Đa số nhu cầu LLMOps thực tế dừng ở bước 1-2.
- Mentor nhiều lần ưu tiên "hoàn thiện luồng" trước khi mở rộng hạ tầng (đúng
  tinh thần lần quyết định tránh đi sâu gitops-for-model trước đây).
- Khả năng "dựng pipeline train/fine-tune" đã được chứng minh ở MLOps rồi —
  làm lại y hệt cơ chế đó cho 1 LLM qua LoRA không chứng minh thêm năng lực
  mới, chỉ lặp lại kỹ năng cũ trên artifact khác.
- Phần thực sự CHƯA được chứng minh trong repo là đúng phần đặc thù LLMOps:
  prompt versioning, RAG ingest→evaluate→deploy, và `routers/chat.py` (hiện
  chỉ là stub trả về text giả).

**Kết luận phạm vi: LLMOps lifecycle = prompt + RAG + evaluate + deploy,
không có bước train/fine-tune.**

## 5. Luồng RAG ingest→evaluate→deploy cụ thể là gì

Ánh xạ vào đúng adapter đã có sẵn trong repo (`adapters/interfaces.py` và
implementation của nó):

1. **Ingest** — tài liệu nguồn (vd `docs/`, README từng service/adapter, hoặc
   runbook vận hành) → chia nhỏ thành đoạn (chunking) → mỗi đoạn chạy qua
   **embedding model** (bước hiện đang thiếu hoàn toàn — xem câu hỏi mở #1) →
   lưu (vector + text gốc + metadata) vào Qdrant qua `QdrantAdapter.upsert()`
   (method đã có sẵn, hiện chưa ai gọi tới trong toàn repo). Kết quả: 1 "phiên
   bản index" mới — vai trò tương đương bước "Track" bên MLOps (dataset
   lineage).
2. **Evaluate** — chạy 1 bộ câu hỏi mẫu cố định (eval set) qua RAG pipeline:
   `QdrantAdapter.search()` lấy đoạn liên quan từ index mới → ghép vào prompt
   → `LiteLLMGatewayAdapter.chat_completion()` → câu trả lời → chấm bằng
   LLM-as-judge đã có sẵn (`evaluations/llm_judge.py` + `evaluations/gate.py`,
   cùng cơ chế đang dùng cho MLOps Golden Path #2). Tỷ lệ pass đủ cao → index
   được coi là đủ tốt.
3. **Deploy** — `routers/chat.py` (hiện là stub, chưa gọi LLM/MCP/RAG gì cả)
   khi phục vụ người dùng thật sẽ retrieve từ đúng phiên bản index đã được
   Evaluate Gate duyệt, không phải bản mới nhất chưa kiểm chứng. "Deploy" =
   đổi 1 con trỏ "index/prompt nào đang active" (tức thời hay qua PR — xem
   câu hỏi mở #2).

Prompt versioning đi theo đúng khuôn tương tự: Draft/sửa prompt → Evaluate
(LLM-as-judge trên eval set câu hỏi-đáp mẫu) → Register version → Deploy
(kích hoạt làm system prompt đang sống cho `chat.py`).

## 6. Thành phần đã có sẵn — tái dùng, không viết lại

| Thành phần | Trạng thái | Vị trí |
|---|---|---|
| Prompt Registry UI | Chạy được, chỉ đọc (read-only), backend in-memory | `plugins/prompt-registry/`, `routers/prompts.py` |
| Prompt Registry (code-side) | Hằng số tĩnh, trùng lặp thủ công với bản UI | `agents/prompts/system_prompts.py` |
| LLM Gateway (LiteLLM) adapter | Đã implement, mới cấu hình 1 model (Claude Sonnet 5) | `adapters/llm_gateway_adapter.py`, `infra/llm-gateways/litellm-config.yaml` |
| LLM-as-judge / Evaluate Gate | Đã implement, đi qua LiteLLM adapter đúng chuẩn | `evaluations/llm_judge.py`, `evaluations/gate.py` |
| Vector DB (Qdrant) adapter | Đã implement upsert/search — **chưa có bước embedding, chưa có pipeline ingest, chưa ai gọi RAG retrieval ở đâu cả** | `adapters/vector_db_adapter.py` |
| Chat endpoint | **Chỉ là stub** — không gọi LLM thật, không route MCP tool | `services/orchestration-api/routers/chat.py` |
| MCP servers | 3 server có sẵn (mlops thật, k8s mock, metrics thật qua Prometheus) — không server nào liên quan RAG/embedding | `agents/mcp-servers/*/server.py` |

## 7. Khoảng trống cần lấp (nếu triển khai)

1. Biến `chat.py` từ stub thành endpoint gọi LLM thật + retrieve RAG + dùng
   đúng prompt version đang active.
2. Pipeline ingest RAG thật — hiện chưa có gì gọi `QdrantAdapter.upsert()`.
3. Gộp 2 nơi lưu prompt đang trùng lặp (`routers/prompts.py` in-memory vs
   `agents/prompts/system_prompts.py` tĩnh) thành 1 nguồn sự thật duy nhất, có
   cơ chế tạo version mới (hiện chỉ có GET, không có POST/register).
4. 1-2 Software Template (Golden Path) mới trong `examples/templates/`, theo
   đúng pattern đã dùng cho MLOps — Custom Scaffolder Action gọi HTTP sang
   orchestration-api, không đặt business logic trong Backstage.
5. (Tuỳ chọn) thêm model thứ 2 vào `litellm-config.yaml` nếu muốn minh hoạ
   Gateway multi-model thật — playbook nhắc "case thật: Qwen" như ví dụ slide,
   không phải yêu cầu kỹ thuật bắt buộc.

## 8. Câu hỏi mở — CẦN CHỐT trước khi triển khai

1. **RAG scope / cách tạo embedding**:
   - (a) Self-hosted embedding model chạy local (vd sentence-transformers
     all-MiniLM-L6-v2, pip install runtime như cách đã làm với training
     container) — không cần thêm API key trả phí. *(đề xuất)*
   - (b) Voyage AI embedding API — chất lượng cao hơn, cần thêm `VOYAGE_API_KEY`.
   - (c) Bỏ RAG đợt này, chỉ làm prompt versioning — phạm vi nhỏ hơn nhưng
     thiếu đúng 1 trong 3 trụ cột LLMOps mà playbook đã định nghĩa.

2. **Lưu trữ prompt/RAG-index version ở đâu** (repo không có DB cho
   orchestration-api dùng):
   - (a) File YAML + Git commit/PR, giống Golden Path #2 của MLOps — có audit
     trail, nhưng deploy sẽ chậm hơn (phải chờ merge).
   - (b) File JSON local trên orchestration-api, active ngay sau khi Evaluate
     Gate pass — đơn giản, tức thời, nhưng mất dữ liệu khi container restart
     (chấp nhận được vì đây là demo/dev, không phải production nhiều instance).
   - Gợi ý từ phần 3: vì "deploy" LLMOps vốn nên nhẹ/nhanh hơn MLOps, có thể
     nghiêng về (b), nhưng cần xác nhận lại với người dùng.

3. **Hình dạng Golden Path**:
   - (a) 2 template riêng, đúng cấu trúc MLOps: LLM Golden Path #1
     "Ingest/Draft → Evaluate → Register", LLM Golden Path #2
     "Register → Deploy". *(đề xuất — giữ đúng tinh thần song song 2 lifecycle)*
   - (b) 1 template gộp: Draft/Ingest → Evaluate → Register → Deploy trong
     cùng 1 luồng — đơn giản hơn cho người dùng nhưng không cho phép "chỉ
     evaluate mà chưa deploy ngay".

4. **Deploy tức thời hay qua PR** (liên quan trực tiếp câu hỏi 2): xem phần 3
   — pain point LLMOps cần phản hồi nhanh, nghiêng về tức thời sau khi
   Evaluate Gate pass, nhưng chưa chốt.

5. **Model thứ 2 (Qwen qua Ollama...)**: đã chốt SƠ BỘ là không cần trong đợt
   hoàn thiện lifecycle này (xem phần 4) — có thể làm stretch goal riêng sau.
