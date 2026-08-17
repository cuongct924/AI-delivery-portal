# Plugins Workspace (ghi chú, chưa có code)

Backstage app thật (tạo bởi `scripts/setup-backstage.sh`) sẽ có custom plugin
nằm trong chính nó, ở `packages/backend/src/plugins/` hoặc `plugins/<ten-plugin>/`
tùy theo bạn dùng New Backend System hay không (xem docs/architecture.md).

Thư mục này chỉ dùng để **ghi chú thiết kế** trước khi code, ví dụ:

- `custom-actions-design.md` — liệt kê các Custom Scaffolder Action cần viết
  (VD: `mlops:check-evaluation-gate`, `mlops:trigger-deploy`) và endpoint
  FastAPI tương ứng mà mỗi action sẽ gọi tới.

Khi thực sự viết plugin (tuần 2-3), code nằm trong app Backstage thật, không
nằm trong repo labs này — tránh nhầm lẫn 2 nơi.
