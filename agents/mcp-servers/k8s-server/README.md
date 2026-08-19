# k8s-server

MCP server exposing the `check_pod_status`, `get_logs` tools — currently
**mock** (not wired to a real K8s cluster). Integrate the `kubernetes` Python
client when the infrastructure phase begins (see `docs/roadmap.md`, week 8+)
and add RBAC/OPA policy in `infra/opa-policies/` before granting write access.

## Run locally

```bash
bash scripts/run-mcp-local.sh k8s
```
