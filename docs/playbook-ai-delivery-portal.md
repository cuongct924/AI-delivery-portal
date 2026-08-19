# REFERENCE PLAYBOOK
## AI Delivery Portal — Internal Developer Platform for MLOps/LLMOps
### Viettel Digital Talent 2026 · Cloud Track · Phase 2

---

## 0. COMPASS — 3 CORE QUESTIONS TO USE THROUGHOUT THE JOURNEY

Whenever unsure "should I build this feature", "should I prioritize this" — come back to these 3 questions:

1. **What happens most often?** (Frequency) — the more it repeats, the higher the ROI of automating it.
2. **What's most error-prone?** (Error-proneness) — the more prone to manual mistakes, the more it needs a policy/template to prevent them upfront.
3. **What carries the highest risk if done wrong?** (Impact/Blast radius) — the bigger the impact (production, many teams), the tighter the control gate needs to be.

### Priority matrix (use for every design decision)

```
                    Low risk                 High risk
High frequency │  Light automation        │  TOP PRIORITY
               │  (e.g. logging an        │  (e.g. deploying to
               │  experiment)              │  production)
───────────────┼──────────────────────────┼───────────────────────────
Low frequency  │  Lowest priority          │  Stretch goal, worth
               │  (e.g. notebook setup)    │  doing if time remains
               │                           │  (e.g. rollback)
```

**Principle**: always prioritize the "high frequency × high risk" cell first — this is where the golden path creates the most value and is easiest to measure (benchmark).

---

## 1. PROJECT POSITIONING — THE CORE STORY

> *"Viettel's AI Platform already has strong capabilities (Registry, Experiment, Inference, Notebook), but lacks a standardized connecting layer. The Portal doesn't replace these systems — it's a DevEx/orchestration layer sitting on top, turning a fragmented, manual, error-prone process into an automated, safe, measurable golden path."*

### Why this project is "better" than it first seems

- This isn't just "building a CI/CD portal" — it's **Platform Engineering applied to the MLOps domain**, a field that's very hot right now.
- High real-world value: exactly what leadership needs → if done well, the product has a real chance of being used, not just shelved after the defense.
- Enough technical depth if tapped correctly: design patterns, adapter architecture, policy-as-code, MLOps/LLMOps domain knowledge.

### Core knowledge structure (4 pillars, not 2)

```
1. Software Engineering       → foundation (design patterns, API design)
2. Platform Engineering/DevOps → MAIN BODY (IDP, Golden Path, K8s, GitOps)
3. DevSecOps                  → one facet within it (policy-as-code, OPA)
4. MLOps/LLMOps domain        → the part that makes this project DISTINCTIVE, can't be skipped
```

---

## 2. GOLDEN PATH — FOUNDATIONAL CONCEPT

### Definition

> **Golden Path = a pre-paved, easiest-to-follow road, standardized with best practices, for completing a recurring task — making "doing it right" the easiest choice, without force.**

### Where it fits in the bigger picture

```
Internal Developer Platform (IDP)   ← philosophy/goal ("self-service for devs")
        └── Golden Path             ← how it's realized (the standard path)
                └── Backstage        ← the specific tool used to build it
```

### 6 foundational principles (universal, applies to every company)

1. **"Paved road, not the only road"** — a recommendation, not an absolute mandate.
2. **Reduces cognitive load** — the system "remembers" best practices for you, devs don't need to memorize everything.
3. **Self-service** — devs can act immediately, without waiting on someone else.
4. **Starts from a real pain point** — not from "we have a cool tool, let's shove it in".
5. **Measurable** — has metrics: adoption rate, time saved, fewer errors.
6. **A living product** — needs maintenance, periodic updates, not built once and abandoned.

### What differs between companies (no single universal template)

| Factor | Impact on Golden Path design |
|---|---|
| Existing infrastructure | The golden path must anchor to real infrastructure, not copy another company's template verbatim |
| Scale/maturity | A large organization (like Viettel) → needs more gates/governance |
| Culture | Viettel (telecom, needs stability) → prioritizes safety over raw speed |
| Workload type | MLOps has its own specifics, different from typical DevOps (see section 3) |

**→ For Viettel**: the golden path should have clear policy gates, full audit trails, and **leave an escape hatch** for edge cases (not force 100% of work through the Portal).

---

## 3. THE MODEL LIFECYCLE — DIRECTLY SHAPES THE DESIGN

```
Train → Experiment → Evaluate → Register → Deploy → Monitor → Retrain ─┐
  ↑                                                                    │
  └──────────────────────────────────────────────────────────────────┘
        (a loop, NOT a straight line like typical CI/CD)
```

### Mapping table: Domain Knowledge → Design decisions

| Domain Knowledge | Golden Path affected | Concrete design change |
|---|---|---|
| Model versioning ≠ Code versioning | #1 Register | Needed metadata: `git_commit_hash` + `dataset_version` + `hyperparameters`, not just the model file |
| Data lineage | #1 Register | Add `data_source_uri`, `data_snapshot_id` fields |
| Evaluate is a hidden gate (not among the 4 systems listed in the brief) | Between #1 and Register | A self-discovered insight — emphasize this during the defense |
| Model drift | #2 Deploy → Monitor | Dashboard needs distribution/drift metrics, not just uptime |
| A/B testing a model | #2 Deploy | Support Canary/Shadow deploy, not just simple Blue-Green |
| Prompt versioning (LLMOps) | Registry extension | A Prompt Registry separate from the Model Registry |
| RAG (LLMOps) | Overall architecture | Add a Vector DB if going deep on LLM |
| Evaluating LLM text output | Evaluate gate | Needs LLM-as-judge, not a simple accuracy threshold |

### Sample answer for "How is your golden path different from regular CI/CD?"

> *"Regular CI/CD is linear, serving code. The MLOps golden path has to correctly model the cyclical nature and its specific gates — especially Evaluate (checking model quality before promotion) and Retrain (closing the loop when a model degrades) — concepts that don't exist in typical software CI/CD."*

---

## 4. SYSTEM ARCHITECTURE

```
┌────────────────────────────────────────────┐
│         Portal UI (Backstage)                 │
├────────────────────────────────────────────┤
│   BFF / Orchestration API (FastAPI)            │
│   - Auth (Keycloak) - Golden Path Engine        │
│   - Workflow trigger (Argo Workflows)           │
├───┬────────┬────────┬────────┬────────────┤
│Registry│Experiment│Inference│Notebook│      Adapter Layer
│Adapter │ Adapter  │ Adapter │Adapter │      (shared interface)
├───┴────────┴────────┴────────┴────────────┤
│ MLflow │ MLflow   │ KServe/ │Kubeflow│      Real/mock backend
│Registry│ Tracking │BentoML  │Notebook│      (swappable without touching the Portal)
└────────────────────────────────────────────┘
   Cross-cutting: OPA (policy) | Prometheus/Grafana (observability)
                  | ArgoCD + Helm (GitOps CD)
```

### The single most important design principle

**The Adapter Pattern is the backbone**: each subsystem goes through one shared interface → mock it first, plug in the real system later, without modifying the Portal.

```python
class IModelRegistryAdapter(ABC):
    def register_model(self, name, version, artifact_uri) -> ModelInfo: ...
    def list_models(self, project) -> List[ModelInfo]: ...


class MLflowRegistryAdapter(IModelRegistryAdapter): ...  # mock/real if Viettel uses MLflow


class ViettelRegistryAdapter(IModelRegistryAdapter): ...  # write this once real info is available
```

---

## 5. TECH STACK — CROSS-CHECKED AGAINST GOVERNANCE (avoid misstatements when questioned)

| Layer | Technology | Foundation |
|---|---|---|
| Portal UI | **Backstage** | ✅ CNCF Graduated |
| Orchestration API | FastAPI (Python) | Independent |
| Golden path template | Backstage Software Templates | (part of Backstage) |
| Auth | Keycloak | Independent (Red Hat), not CNCF |
| Model Registry + Experiment | **MLflow** | LF AI & Data Foundation (NOT CNCF) |
| Inference | **KServe** (or the lighter BentoML) | LF AI & Data Foundation |
| Notebook | Kubeflow Notebooks / JupyterHub | LF AI & Data / independent |
| CI | GitLab CI | Independent |
| CD/GitOps | **ArgoCD** | ✅ CNCF Graduated |
| Packaging | **Helm** | ✅ CNCF Graduated |
| Policy | **OPA** | ✅ CNCF Graduated |
| Observability | Prometheus (✅ CNCF) + Grafana/Loki (❌ not CNCF, Grafana Labs) | Mixed |

**Standard talking point for presentations**: *"We prioritize CNCF projects for the infrastructure/platform layer (Backstage, ArgoCD, Helm, OPA, Prometheus), combined with industry-standard MLOps projects under the LF AI & Data Foundation (MLflow, Kubeflow, KServe) — the entire stack is open-source, avoiding vendor lock-in."*

### Languages used

| Language | Used for |
|---|---|
| Python | Backend/API, Adapters, benchmark scripts |
| TypeScript/React | Backstage custom plugin |
| YAML | K8s manifests, Helm, Argo Workflow, Backstage Template |
| Rego | Writing OPA policy rules (learn separately, 1-2 days) |
| Bash | Utility scripts |

---

## 6. DESIGN PATTERNS — THE 4 TO USE (don't cram in all 8)

| Pattern | Where it's applied | Why it's "worth mentioning" in the defense |
|---|---|---|
| **Adapter** | Connects MLflow/KServe/the real systems | The core — lets backends be swapped without touching the Portal |
| **Template Method** | Defines the standard Golden Path skeleton, allows per-step overrides | Matches EXACTLY the "standard but customizable path" nature of a Golden Path |
| **Chain of Responsibility** | Policy-check chain (OPA): resource limit → security scan → evaluation-passed | Matches the mechanism for enforcing several sequential conditions |
| **Factory** | Picks the right Adapter based on config | Pairs naturally with Adapter, easy to extend |

*(Facade, Strategy, Observer, Builder are secondary patterns — know them well enough to use where appropriate, no need to list all of them in the defense)*

---

## 7. SCOPE — HOW MUCH GOLDEN PATH TO BUILD

### Decision: 2 core golden paths + 1 stretch goal

| # | Golden Path | Role | Investment |
|---|---|---|---|
| 1 | **Train → Track → Register** | Standardizes the input side, addresses "high frequency" | Moderate |
| 2 | **Register → Deploy** | Addresses both "most error-prone" + "highest risk" | **Deepest — the focus** |
| 3 (stretch) | Rollback/Promote version | Adds onto #2, doesn't need to be its own path | If time allows (week 10-11) |

**Why not do more**: Claude Code helps code faster, but does NOT shorten the time needed for design, real integration, testing, and benchmarking — that's the real bottleneck, not writing code.

**Notebook**: only integrate at the minimum level (a redirect link), does NOT need its own golden path — far lower value than the two above.

---

## 8. 12-WEEK ROADMAP

| Week | Content |
|---|---|
| 1 | Ask the mentor questions (see checklist in section 10). Read up on Golden Path/IDP/Backstage concepts BEFORE coding. Basic Backstage test-drive |
| 2-3 | Lab setup: MLflow, fake GPU/mock inference, write Adapter interface + Mock Adapter |
| 4-5 | Write the real Adapter if access is granted; write the BFF API (FastAPI) in parallel |
| 6-7 | Golden Path #1: Train → Track → Register (Argo Workflows) |
| 8-9 | Golden Path #2: Register → Deploy (Helm template + ArgoCD + OPA policy) |
| 10 | Observability dashboard, start benchmarking; stretch: Rollback |
| 11 | Finalize the report, slides, record a backup demo video, write a production roadmap |
| 12 | Practice presentation with the mentor, revise, prepare for Q&A |

---

## 9. BENCHMARKS — HOW TO PROVE VALUE WITH DATA

### General principles
1. Have a clear baseline (manual / default).
2. Measure under the same conditions.
3. At least 3 kinds of metrics: effectiveness, savings, experience.
4. Visual charts, not just tables of numbers.

### Benchmark suite for the Portal (self-measurable, no need to wait for real users)

| How to measure | Example figures |
|---|---|
| Manual steps vs. through the Portal (self-measured, repeated multiple times) | "Manual deploy: 25 min/12 steps → via Portal: 3 min/2 steps, an 88% reduction" |
| Fault injection (deliberately introduce common config errors) | "20 error scenarios: manually, 14/20 slip through to production; via the golden path, 18/20 are blocked" |
| Standardization coverage | "70% of manual touchpoints eliminated thanks to the golden path" |
| Small A/B with colleagues (if possible) | Average completion time, a small sample is still valuable at an internship scale |
| System performance | API latency, orchestration layer throughput |

**Presentation note**: emphasize "measured repeatedly, across many scenarios" rather than trying to claim "large scale" — a small sample is still convincing if repeated under control.

---

## 10. CHECKLIST OF QUESTIONS FOR THE MENTOR (do this in week 1)

- [ ] What does the current AI Platform run on — self-built, or MLflow/Kubeflow/Seldon?
- [ ] What's currently serving inference — KServe, Seldon, Triton, or custom?
- [ ] Is there an internal API/SDK the Portal can call into? Can a service account be granted?
- [ ] What does current auth use (SSO/LDAP/Keycloak)?
- [ ] On average, how long does the team currently take to deploy a model? (→ a golden number for the problem-statement slide)
- [ ] Have there been incidents caused by lack of standardization/missing health checks?
- [ ] Is there a clear rollback process, or is it handled manually?
- [ ] Is a dedicated lab cluster available for dev/test?
- [ ] Does Viettel have a real internal need for LLM/chatbot use cases right now? (decides whether to go deep on LLMOps)

**Principle**: even getting just 1-2 real numbers/stories means the gap is no longer an assumption — it's a problem confirmed by an insider. This is the difference between a defense that "sounds reasonable" and one that's genuinely convincing.

---

## 11. DEFENSE SLIDE STRUCTURE (15-18 slides)

```
Part 1 — Introduction & Problem (3 slides)
  1. Cover slide
  2. Current AI Platform context
  3. ⭐ The real problem (pain point backed by data) — THE MOST IMPORTANT SLIDE

Part 2 — Solution & Architecture (5-6 slides)
  4. Solution overview (before/after)
  5. System architecture
  6. Technology Justification (CNCF/LF AI & Data)
  7. Golden Path #1
  8. Golden Path #2 (the focus)
  9. Adapter Pattern / extensibility

Part 3 — Demo & Results (4-5 slides)
  10. Demo (live + backup video)
  11. Time/step-count benchmark
  12. Blocked-error-count benchmark
  13. Observability dashboard

Part 4 — Evaluation (2 slides)
  14. Current limitations (proactively state them, shows honesty)
  15. Lessons learned

Part 5 — Vision (2 slides)
  16. ⭐ Roadmap to Production — THE 2ND MOST IMPORTANT SLIDE
  17. Conclusion
```

**The 2 slides that decide "standing out"**: Slide 3 (The real problem) and Slide 16 (Production roadmap) — these are the two places that show practical/business thinking, not just pure technical work, which is exactly what helps you stand out for a full-time offer.

---

## 12. SAMPLE ANSWERS FOR TOUGH QUESTIONS

**Q: "Why not just use the existing Backstage/MLflow/Kueue as-is, why build your own?"**
> "I'm not rewriting these systems — the Portal is a DevEx/orchestration layer on top, using proven CNCF/LF AI & Data projects already validated at large-scale production. My value lies in designing golden paths that fit Viettel's specific MLOps needs, integrating them into one standardized flow with policy enforcement, and benchmarks that prove the impact — something using each tool in isolation doesn't give you on its own."

**Q: "Your golden path stops at Deploy — what happens when the model degrades?"**
> "I designed the Monitor dashboard as the foundation for the Retrain loop — given the 3-month timeframe, the automatic retrain-trigger piece is in the proposed roadmap (slide 16), but the current architecture is already built to extend, since the Adapter pattern lets a new step be plugged in without breaking the design."

**Q: "Can you actually measure objective benchmarks — is a small sample reliable?"**
> "I benchmark two ways: (1) self-measured, repeating the same scenario multiple times (manual vs. via the Portal) for reliability through repetition, and (2) fault-injection with controlled error scenarios — neither depends on having a large number of real users, which fits the 3-month timeframe."

---

## 13. LEARNING RESOURCES — A CURATED LIST (no need to read everything, pick by phase)

### Courses (priority, hands-on heavy)
- **MLOps Zoomcamp** (DataTalks.Club) — free, 3 months, uses the exact MLflow/Docker/Prometheus/Grafana/GitHub Actions stack — closest match to this project.
- **Made With ML** — free, teaches building an end-to-end ML system (tracking, testing, serving, monitoring).
- **Full Stack Deep Learning — LLM Bootcamp** — the "LLMOps: Deployment and Learning in Production" module, use if going deep on LLMOps.

### Books
- *Introducing MLOps* (Mark Treveil & Dataiku Team) — intro-level, enterprise context (fits Viettel).
- *Practical MLOps* — hands-on CI/CD for ML, infrastructure, monitoring.
- *Building Machine Learning Pipelines* (Hapke & Nelson) — deep dive on pipelines/orchestration.

### Technical documentation
- `mlflow.org/docs` — read "Model Registry" + "Tracking" carefully before writing the Adapter.
- `kserve.github.io/website` — the "InferenceService" concept.
- `backstage.io/docs/overview/what-is-backstage` — read "Concepts" before coding.
- The original **"Golden Paths" — Spotify Engineering** blog post (read the original, where the concept originated).
- `platformengineering.org` — Platform Engineering definitions & case studies.

### Academic papers (cite for the Related Work section, no need to implement)
- *Themis: Fair and Efficient GPU Cluster Scheduling* (NSDI 2020) — if you want to cross-reference fairness.
- (Mainly a reference point for large-scale MLOps systems thinking — not required for the Portal project, more relevant to the Scheduler side if applicable.)

---

## 14. OVERALL GUIDING PRINCIPLES (apply to every decision over the 3 months)

1. **Always come back to the 3 core questions** (section 0) when unsure what to do first.
2. **Depth > breadth** — 2 golden paths done thoroughly beats 4 done superficially.
3. **Every design decision needs a reason** — don't pick a technology/pattern "because it looks cool", always be able to answer "why this one".
4. **Proactively state limitations** rather than let the committee find them — shows honesty, professionalism.
5. **Real numbers from Viettel > assumed numbers** — spend time asking the mentor as early as possible.
6. **The Adapter Pattern is insurance** — designed to switch from mock to real without rewriting anything.
7. **Don't just do a school project — think like a real Platform Engineer**: the golden path must solve a real pain point, be measurable, and have a path to production.

---

*This playbook should be reviewed at the end of each major phase (after week 3, week 7, week 10) to adjust based on what actually comes up while working with the mentor and Viettel's real systems.*
