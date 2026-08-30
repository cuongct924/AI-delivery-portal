# golden-paths-server

MCP server for the LLMOps Lifecycle Golden Path actions — the "action"
domain (mutates state), separate from `mlops-observability-server`'s
read-only "health" domain. Each tool is a thin HTTP client into
`services/orchestration-api`'s existing `/prompts` and `/rag` endpoints — no
business logic lives here.

Tools:
- `draft_prompt`, `evaluate_prompt`, `rag_ingest`, `rag_evaluate` — auto-executable.
- `activate_prompt`, `rag_activate` — tagged `destructive_hint=True`. LLMOps
  activation is Instant (no PR-gate, unlike MLOps) — so these tools are the
  *only* safety gate LLMOps has. `routers/chat.py`'s tool-calling loop must
  never call these directly; it should surface a proposal and wait for
  explicit user confirmation instead.

## Auth and traceability

This server has its own verifiable identity — a Keycloak service-account
client (`golden-paths-agent`, `serviceAccountsEnabled=true`, realm
`ai-delivery-portal`, provisioned by `infra/keycloak/realm-export.json`).
`keycloak_client.py` fetches/caches a `client_credentials` access token and
attaches it as `Authorization: Bearer <token>` on every call.

`orchestration-api`'s `auth/keycloak.py` verifies this token for real
(signature, audience) **regardless of its own `AUTH_ENABLED` setting** — a
caller that presents a token always gets it checked; only a caller with no
token at all falls back to the `AUTH_ENABLED=false` dev-bypass identity
(which Backstage Scaffolder actions rely on today — see
`packages/backend/src/actions/mlopsActions.ts`'s `postJson`, which sends no
auth header). This means: no need to flip `AUTH_ENABLED=true` globally to
get a trustworthy identity for the Agent, and the human path is unaffected.
Verified live: a request with this server's real token logs
`authenticated as golden-paths-agent`; a request with no token logs
`authenticated as local-dev`; an invalid token gets a real 401, not a
silent fallback.

**Still a known limitation**: `orchestration-api`'s Keycloak client
(`keycloak_client_id="orchestration-api"`) and human login are not
provisioned by `infra/keycloak/realm-export.json` — only this server's own
service-account client is. If a fresh Keycloak volume doesn't already have
the rest of the realm configured, human/Scaffolder calls still work fine
(no token sent, dev-bypass), but nothing else Keycloak-related is
automated yet.

Transport: `streamable-http`, `MCP_HOST`/`MCP_PORT` (default `0.0.0.0:9002`)
— discovered at runtime via the Backstage Catalog
(`services/orchestration-api/catalog_client.py`), not a hardcoded local path.

## Run locally

```bash
bash scripts/run-mcp-local.sh golden-paths
```
