# monitoring

Configuration for tracking model/system health — Prometheus scraping +
Grafana dashboards.

- `prometheus.yml` — scrape config that **works right away** via
  `docker compose up` (`prometheus` service, UI at `http://localhost:9090`).
  `agents/mcp-servers/metrics-server/` reads data from here to answer Claude
  when asked whether a model is drifting or slow.
- `grafana/` — **works right away** via `docker compose up` (`grafana`
  service, UI at `http://localhost:3001` — host port 3001, since Backstage's
  dev server already owns 3000). Auto-provisioned on startup, no manual
  setup: `grafana/provisioning/datasources/prometheus.yml` wires up
  Prometheus as the default datasource, `grafana/provisioning/dashboards/`
  auto-loads any dashboard JSON dropped into `grafana/dashboards/`.
  `grafana/dashboards/orchestration-api.json` is a starter dashboard
  (request rate, p95 latency, total requests) built from the metrics
  `services/orchestration-api/main.py` already exposes at `/metrics`.
  Anonymous viewer access is enabled for convenience; login is `admin`/`admin`
  if you need to edit anything.
- ServiceMonitor (CRD for Prometheus Operator on a real K8s cluster) —
  not implemented yet, week 8+ once a real cluster exists (see
  `docs/roadmap.md`).
