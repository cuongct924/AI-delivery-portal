# 12-week roadmap (progress tracker)

Copied from the playbook, used to tick off progress directly in the repo (commit regularly).

- [ ] **Week 1** — Backstage + MLflow test-drive (day 1 done). Read up on
      Golden Path/IDP concepts. Questions for the mentor (separate checklist
      in playbook section 10).
- [ ] **Week 2-3** — Full lab setup: Mock Inference (FastAPI), write the
      `IModelRegistryAdapter` interface + `MLflowRegistryAdapter`. First
      Custom Scaffolder Action that calls real MLflow.
- [ ] **Week 4-5** — Write the real Adapter for Viettel's system (if access
      is granted). Set up `services/orchestration-api/` (FastAPI).
- [ ] **Week 6-7** — Golden Path #1: Train → Track → Register (Argo Workflows).
- [ ] **Week 8-9** — Golden Path #2: Register → Deploy (Helm + ArgoCD + policy
      check — OPA if time allows, manual validation otherwise).
- [ ] **Week 10** — Observability dashboard (Prometheus/Grafana). Start benchmarking.
      Stretch goal: Rollback (if time permits).
- [ ] **Week 11** — Finalize benchmarks, write the report, slides, record a backup demo video.
- [ ] **Week 12** — Practice presentation with the mentor, revise, prepare for Q&A.

## Cut-loss checkpoints (self-check weekly)

| If by... | You haven't yet... | Then... |
|---|---|---|
| Week 3 | Gotten a custom Backstage plugin running | Switch to a Portal written in plain React |
| Week 6 | Finished Golden Path #1 | Drop the LLMOps expansion branch entirely (Prompt Registry/RAG) |
| Week 9 | Gotten Golden Path #2 with a policy check | Drop OPA, replace with manual validation logic in FastAPI |
| Week 10 | Got at least one benchmark suite | Absolute priority on manually measuring benchmarks vs. the Portal |
