# Overall architecture (quick reference)

The full details live in `playbook-ai-delivery-portal.md` (sections 4-6). This
file is just a summary for quick lookup while coding.

```
┌────────────────────────────────────────────┐
│         Portal UI (Backstage)                 │  ← packages/app-backstage, packages/backend
├────────────────────────────────────────────┤
│   BFF / Orchestration API (FastAPI)            │  ← services/orchestration-api/ (week 4+)
│   - Auth (Keycloak) - Golden Path Engine        │
│   - Workflow trigger (Argo Workflows)           │
├───┬────────┬────────┬────────┬────────────┤
│Registry│Experiment│Inference│Notebook│      ← adapters/ (shared interface)
│Adapter │ Adapter  │ Adapter │Adapter │
├───┴────────┴────────┴────────┴────────────┤
│ MLflow │ MLflow   │ KServe/ │Kubeflow│      ← real/mock backend
│Registry│ Tracking │BentoML  │Notebook│
└────────────────────────────────────────────┘
   Cross-cutting: OPA (policy) | Prometheus/Grafana | ArgoCD + Helm
```

## Invariant principles (don't violate these when coding)

1. **The Custom Scaffolder Action in Backstage does NOT contain business
   logic itself** — it only makes an HTTP call to the FastAPI Backend. All
   Adapter/Factory/Chain of Responsibility logic lives in Python
   (`services/orchestration-api/` once created).
2. **Every Adapter implements the same shared interface**
   (`IModelRegistryAdapter`, `IInferenceAdapter`...) — so switching from Mock
   to a real self-hosted backend only requires adding one new class, without
   touching existing code.
3. **2 core Golden Paths**: Train→Track→Register, Register→Deploy. Do not add
   a third golden path unless the first two are already stable (see `roadmap.md`).

## Design patterns — where they're applied

| Pattern | Where |
|---|---|
| Adapter | `adapters/*.py` — connects to MLflow/KServe/the real system |
| Factory | `adapters/factory.py` — picks the right Adapter based on config |
| Template Method | The Backstage Scaffolder itself (`template.yaml` steps) — no custom code needed |
| Chain of Responsibility | `services/orchestration-api/policies/` — policy-check chain (OPA or manual validation) |
