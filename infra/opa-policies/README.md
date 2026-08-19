# opa-policies

RBAC policy (Rego) controlling Agent permissions when executing commands —
e.g. blocking `k8s-server` (agents/mcp-servers/k8s-server/) from performing
write/delete operations, read-only allowed. **Not implemented yet — week 8+**
(`docs/roadmap.md`), to be written alongside `k8s-server`'s move from mock to
a real cluster connection.
