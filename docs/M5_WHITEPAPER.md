*[🇩🇪 Deutsche Version](M5_WHITEPAPER.de.md)*

# M5 — Definition of Done as a Research Engine

> A pattern for self-evaluating multi-tool systems.
> Whitepaper draft, state: 2026-05-10 (after Phase 6.4).
> Deep-dives in [`STAR.md`](STAR.md), [`LIFECYCLE.md`](LIFECYCLE.md), [`OBSERVABILITY.md`](OBSERVABILITY.md), [`DEMOS.md`](DEMOS.md).

## Abstract

Multi-tool systems with autonomous actions suffer from an implicit gap: **what counts as a "correct" action?** Tests check code, humans correct reactively, LLM confidence is self-referential. M5 closes this gap with a two-part rule:

> **Before every action with external effect, the system researches the Definition of Done from six prioritized sources. If it cannot find a sufficiently clear DoD, it asks the user with targeted follow-up questions — before acting. After the action, it measures fulfillment of the DoD and writes the result back into memory.**

The second sentence is the more important half: DoD is not just pre-action research, but also post-action assessment. Only the closed loop makes the system **evaluative** instead of merely reactive — and writing down failure lessons makes it **self-correcting**.

The DoD research engine is the core of a pattern set built from 5 components (Effectors, Memory, Nervous System, Observation, Lifecycle) and 5 meta-patterns (M1 Pre-Lookup, M2 Upstream, M3 User-Gate, M4 Corpus-before-Pipeline, M5 DoD). M5 is the connecting joint that turns loose parts into an organism — the system becomes **evaluative** instead of merely reactive.

A reference implementation ships the pattern with 503 tests green; an automated cross-domain test verifies domain independence across three different demo domains (architecture practice, tax advisory, CFO office) with identical pipeline counts.

## 1. Motivation

In any multi-tool system with autonomous actors, the question arises: how do you measure whether an action was correct? Classical success measures don't reach far enough:

- **Tests pass** checks code correctness, not action correctness. An effector that is green in its unit tests can still produce the wrong answer in a concrete domain.
- **Human corrects afterwards** is reactive. The AI has already acted, the user notices the mistake on review, the system learns slowly.
- **LLM confidence** is self-referential. "I'm 92% sure" says nothing about external correctness.

M5 closes this gap with a simple but powerful principle: **the success criteria are made explicit before the action**, researched from multiple sources, in a fixed hierarchy. The AI only acts if it has a sufficiently clear DoD — otherwise it asks back. After the action, fulfillment is measured and the outcome written back as a lesson.

This makes the system **evaluative**: it knows whether what it did was good, without a human having to tell it. Failures are not silently absorbed but written down as lessons — which reappear in the next DoD research and, step by step, make the system **self-correcting**.

## 2. Architectural Context

M5 lives in a system with five building blocks and five patterns:

```
   Domain interchangeable
        ⇡
   Building blocks ① Effectors ② Memory ③ Nervous System ④ Observation ⑤ Lifecycle
        ⇡
   Gold Patterns M1 Pre-Lookup, M2 Upstream, M3 User-Gate, M4 Corpus-before-Pipeline, M5 DoD
        ⇡
   Human at the center
```

### Building blocks

- **① Effectors** — Tools that reach into the world. Implement the five-contact protocol (`pre_load`, `define_done`, `act`, `upstream`, `gate`).
- **② Memory** — Truth store. File-first (YAML+Markdown), no DB as canonical source.
- **③ Nervous system** — Coordination layer (DoD engine, validator, PlanGate, LifecycleManager, Orchestrator).
- **④ Observation** — Observation (TraceStore, LessonsAggregator, EventBus, OTel converter, Provenance).
- **⑤ Lifecycle** — State machine per action kind: `(a) MANUAL → (b) PROPOSED → (c) CHECKED → (d) ROUTINE → (e) AUTONOMOUS`.

### Meta-patterns

- **M1 Pre-Lookup** — Effector reads context (entity profile, lessons, master patterns) **before** the action.
- **M2 Upstream** — Effector reports typed results (Provenance, Lesson, Conflict, Plan) upward.
- **M3 User-Gate** — Write actions with external effect pause and obtain user confirmation.
- **M4 Corpus-before-Pipeline** — Pipeline tweaks are checked against a corpus before they are deployed.
- **M5 DoD** — Before every action the Definition of Done is researched, and after the action it is validated.

M5 is **the synthesis of the other four**: M1 supplies the material for DoD research, M2 carries DoD and fulfillment state upward, M3 is the emergency exit when DoD remains unclear, M4 is DoD at scale.

## 3. The DoD Research Engine

### Star topology

Six sources lie radially around the action. The action is the center, each source a ray:

```
                     (1) EntityFrontmatter
                              │
        (2) Lessons ────┐     │     ┌──── (3) RelatedEntities
                        │     ▼     │
                       ┌─────────────┐
                       │  [ ACTION ] │
                       └─────────────┘
                        │     ▲     │
        (5) DomainPattern ────┘     └──── (4) VectorSearch
                              │
                              ▼
                  (6) UserClarification (terminal)
```

The engine evaluates in **fixed priority 1→6** and stops early as soon as the DoD is clear (`confidence ≥ threshold` AND `clarification_needed empty`).

### The six sources

| # | Source | What it contributes |
|---|---|---|
| 1 | `EntityFrontmatterSource` | Declared DoD criteria from the `frontmatter.dod` block of the referenced entity |
| 2 | `LessonsSource` | What was previously accepted as "done" (user corrections, AUTONOMOUS revision lessons) |
| 3 | `RelatedEntitiesSource` | Cross-reference: similar entities with DoD hints |
| 4 | `VectorSearchSource` | Semantic search in a knowledge base (norms, standards, templates) |
| 5 | `DomainPatternSource` | Domain standards and master patterns |
| 6 | `UserClarificationSource` | Terminal follow-up question when 1-5 are not enough |

### The order is domain-independent and reasoned

- **Specific+concrete first** (Entity > Related > Vector > Pattern): whoever finds the answer in the concrete entity won't ask the vector store.
- **Tried-and-true before normative** (Lessons > Vector): tool-owned lessons beat normative texts because they are grounded in real practice.
- **Normative before asking** (1-5 > User): norms beat user questions, because users don't want their time burned on things already known.

Reversing the order means asking the user things that are already in the frontmatter — that burns user trust.

### Data types

```
Criterion           name, expected, weight, source
SourceContribution  source_name, criteria, confidence_delta,
                    clarifications, evidence
DoD                 criteria, clarification_needed, confidence,
                    evidence_sources, _provenance
                    .is_satisfied_for_act() :: bool
```

### Two different confidence quantities — please don't conflate

M5 distinguishes **two orthogonal** quantities, both of which could be called "confidence/score":

| Quantity | Location | Meaning |
|---|---|---|
| **Definition Confidence** | `DoD.confidence` (before `act()`) | How sure is the system that the DoD itself is well-formulated? Grows with each source contribution; sum-capped `[0,1]`. Drives early-stop and the user-question trigger (UC source). |
| **Fulfillment Score** | `ValidationResult.score` (after `act()`) | How well was the DoD fulfilled? Weighted ratio of satisfied criteria. Drives lifecycle stage transitions. |

A **well-defined DoD with high definition confidence** can have a **low fulfillment score** after the action — that is the normal case of a clearly recognized failure. A **poorly defined DoD** (low definition confidence) should never reach execution — then the UC path (`clarification_needed`) triggers and the action waits for user clarification.

This separation is central to understanding M5: it evaluates **twice** (Before: is the DoD clear enough? After: was it fulfilled?), not once.

### Engine algorithm

```
derive(request, context):
    dod = DoD.empty()
    ctx = dict(context)              # copy to prevent source pollution
    for source in self.sources:                     # priority order
        contribution = source.contribute(request, ctx, dod)
        merge(dod, contribution)
        if dod.confidence >= threshold AND
           not dod.clarification_needed:
            break                                   # early-stop
    return dod
```

**Merge rules**:
- Criteria appended, stamped with `source` via `dataclasses.replace`
- Confidence sum-capped to `[0, 1]`
- Clarifications appended, order-preserving
- Provenance: `source_name → list[criterion_name]`

**Early-stop condition** is conjunctive: confidence threshold AND no open clarifications. Otherwise subsequent sources may fill the clarification or raise the confidence.

Detail: [`STAR.md`](STAR.md).

### When DoD research is dispensable

The naive heuristic "reads are OK, writes need a DoD" is too coarse — a vector search is a read but very much has success criteria (top-N relevance). Sharper heuristic:

- **Dispensable** for **deterministic** operations without room for interpretation (SQL lookup, file read, exact schema match)
- **Dispensable** in stage `(a) MANUAL` — when the human acts, they know themselves
- **Required** for **probabilistic** operations, including reads (vector-search ranking, classification, OCR, AI-driven extraction)
- **Required** from stage `(b) PROPOSED` onward — as soon as the system proposes, a success measure belongs with it
- **Required** for every write action into the truth store
- **Required** for code patches via the self-improvement loop

## 4. Validator and Comparator Semantics

After `act()`, `DoDValidator` checks the result against the DoD. A hybrid comparator strategy supports both DoD definition paths (frontmatter-declared and in-code):

| Form | Example | When | Meaning |
|---|---|---|---|
| `callable` | `lambda v: v > 0` | in-code DoDs | invoked, cast via `bool()` |
| `"lo..hi"` | `"25..35"` | YAML/frontmatter | inclusive numeric range |
| `">=N"` etc | `">=90%"`, `"<5"` | YAML/frontmatter | threshold (`>=`, `<=`, `>`, `<`), optional `%` suffix |
| anything | `True`, `42`, `"approved"` | both paths | equality (`==`) |

**Score** = `sum(weight if satisfied) / sum(all weights)` ∈ `[0, 1]`.

**Conventions**:
- `%` suffix is stripped on both sides (user is responsible for a consistent scale)
- Booleans in numeric contexts are explicitly rejected (Python `bool` is an int subclass, otherwise `True == 1` would skew range tests)
- Callable exceptions are caught, the criterion counts as unsatisfied
- Missing key vs explicit None are distinguished

## 5. M5 + Lifecycle: Maturity Becomes Machine-Assessable

The action lifecycle `(a)→(e)` becomes **machine-assessable only through DoD**:

| Stage | Who checks the DoD | Consequence |
|---|---|---|
| (a) MANUAL | Human acts, no DoD needed | — |
| (b) PROPOSED | System proposes + shows DoD; human confirms | Plan-gate entry contains the DoD |
| (c) CHECKED | System acts + checks itself against DoD; human validates | DoD failure → user notification |
| (d) ROUTINE | System acts + auto-check; human spot-checks | Drift triggers fallback to (c) |
| (e) AUTONOMOUS | System acts + auto-check + revision | Human only on anomaly |

### Stage transitions are avg-score-driven

```
record_outcome(kind, plan_id?, score):
    state.recent_outcomes.append({plan_id, score, recorded_at})
    if len > window_size: trim
    transition = evaluate_transition(state)
    if transition:
        state.stage = transition.to_stage
        state.recent_outcomes = []           # fresh start
        state.transition_history.append(transition)
    persist(state)
```

- **Promote**: avg(last `promote_after_n` outcomes) ≥ `promote_score_threshold` → one stage up
- **Demote** (prioritized): avg(last `demote_after_n` outcomes) < `demote_score_threshold` → one stage back
- **Fresh start** after transition: `recent_outcomes` is cleared, preventing oscillation

Defaults: `promote_after_n=30`, `score≥0.9`; `demote_after_n=5`, `score<0.7`. Settings admin-UI capable.

### AUTONOMOUS revision loop

In stage `(e)` the system executes the action, validates, and on DoD failure a **lesson-feedback loop** runs:

1. Record lesson (provenance: `author="orchestrator", source="autonomous_revision"`)
2. Re-derive the DoD (LessonsSource picks up the new lesson)
3. `act()` again
4. Validate
5. Loop until success or `max_revision_attempts` is reached

The loop is a **human-gated reflection** — the AI tries, but the plan-gate layer and stage discipline prevent the loop from destabilizing the system.

Detail: [`LIFECYCLE.md`](LIFECYCLE.md).

## 6. M5 + Observability: Lesson Feedback Closed

DoD fulfillment is not fed only by static frontmatter criteria — lessons from `(c)/(d)/(e)` outcomes flow via `LessonsSource` back into future `derive()` calls:

```
User correction ──► LessonsAggregator.record_lesson()
                                 │
                                 ▼
                          LessonsStore (file-backed YAML)
                                 │
                                 ▼
                   LessonsSource.contribute()  (in next derive())
                                 │
                                 ▼
                   new Criterion in DoD
```

Match mechanism: `Lesson.context_pattern` is a dict. A lesson matches the current context if all pattern keys/values are present in the context. Empty pattern → matches everything.

LessonsSource has its own `max_confidence_delta` cap to prevent a lesson flood from dominating early-stop.

### Concrete loop example — failure becomes prior knowledge

```yaml
# Action N: extract_floor_plan on a basement entity
# DoD from EntityFrontmatterSource: rooms_count "3..15", parking_as_single_room True
# Effector returns: rooms_count=27 (all <1.5 m²)
# Validation: score=0.30, unsatisfied=[rooms_count, parking_as_single_room]
# AUTONOMOUS revision: max_attempts exhausted, revision_pending=True

# Lesson auto-recorded (Phase 5.0):
lesson:
  id: <uuid>
  kind: extract_floor_plan
  observation: |
    AUTONOMOUS revision attempt 2: validation failed on
    2 criteria (rooms_count, parking_as_single_room)
  context_pattern: {}  # generic, matches everywhere (Phase 4 default)
  provenance:
    author: orchestrator
    source: autonomous_revision
```

```yaml
# Action N+1: extract_floor_plan on the next basement entity
# Engine.derive():
#   1. EntityFrontmatterSource delivers rooms_count "3..15"
#   2. LessonsSource finds the lesson from action N and emits it
#      as a hint into the DoD
#   3. UC source empty (definition confidence sufficient)
# The DoD now additionally contains the hint from the failure loop
```

This way the system learns not only "when it was right" but **what its own weak spots look like** — and feeds that into future DoDs. This is the central coupling between observation (④) and memory (②).

**Phase 4 state**: lesson has `criteria_hint=[]` (no concrete pattern adjustment). A Phase-6+ extension would produce lessons with `proposed_dod_adjustment.add_criterion: {...}` — a distillation from `validation.unsatisfied` into concrete pattern recommendations. Today the lesson is only a marker; the DoD must still be adjusted manually or by external pattern distillation.

### Trace + Provenance + Events

Every `orchestrator.execute()` call produces a **Trace** (`organism.observability.Trace`) with all relevant data:
- `kind`, `request_summary`, `context`, `stage`, `status`
- `dod` (fully embedded)
- `validation` (with score, all_satisfied, unsatisfied)
- `transition_to` (if a stage transition occurred)
- `revision_pending` / `revision_attempts`
- `provenance` (author, timestamp)

Traces are persisted in `traces/{trace_id}.yaml` — file-first, grep-able, OTel-convertible.

**OTel-GenAI mapping**: `trace_to_otel_span(trace) → dict` produces OTel-Semantic-Conventions-compliant JSON with `gen_ai.*` and `organism.*` attributes. Structure-only, no runtime dependency on `opentelemetry-api/sdk` — external exporters (Langfuse, Jaeger, OpenTelemetry Collector) consume the output.

**EventBus** propagates four event types for cross-component logic:
- `plan_proposed` (Orchestrator after `plan_gate.propose`)
- `lifecycle_transition` (Orchestrator after `lifecycle.record_outcome`)
- `trace_recorded` (Orchestrator after trace write)
- `lesson_recorded` (LessonsAggregator after `record_lesson`)

Detail: [`OBSERVABILITY.md`](OBSERVABILITY.md).

## 7. Cross-Domain Validation

Three demo domains implemented in parallel prove the domain independence of the pipeline logic:

| Demo | Domain | Action kind | Effector | Entities |
|---|---|---|---|---|
| `architect_lite` | Architecture practice | `extract_floor_plan` | `FloorPlanExtractor` | 3 floor plans |
| `tax_lite` | Tax advisory | `validate_tax_return` | `TaxReturnValidator` | 3 clients |
| `cfo_lite` | CFO office | `run_close_step` | `QuarterlyCloseRunner` | 3 reporting periods |

All three demos walk through an identical 4-step path:

1. Stage PROPOSED — full propose → approve → apply flow
2. Stage CHECKED — 3 successful actions → promotion to ROUTINE
3. Stage AUTONOMOUS — failing effector → revision loop → `revision_pending=True`
4. Manual HITL lesson via `aggregator.record_lesson()`

### Pipeline counts identical

| Metric | architect_lite | tax_lite | cfo_lite |
|---|---|---|---|
| Actions executed | 6 | 6 | 6 |
| Plans proposed | 1 | 1 | 1 |
| Plans applied | 1 | 1 | 1 |
| Traces recorded | 6 | 6 | 6 |
| Lessons recorded | 3 | 3 | 3 |
| Events captured | 11 | 11 | 11 |
| Transitions observed | 1 | 1 | 1 |
| Final stage | autonomous | autonomous | autonomous |

→ Automatically checked via `tests/examples/test_cross_demo.py`. If this test breaks, genericity is at risk.

### Code ratio

- **Domain code** (`examples/<domain>/`): ~300 lines across 3 demos
- **Pipeline code** (`src/organism/`): ~3000 lines

A fourth domain would again be ~300 lines — genericity has a concrete measure.

Detail: [`DEMOS.md`](DEMOS.md).

## 8. Status & Open Questions

### Reference implementation state (2026-05-10)

- **Phase 0**: Skelett init
- **Phase 1**: Memory + effector contract (Phase 1.1-1.4)
- **Phase 2**: DoD engine + validator (Phase 2.1-2.5, the core)
- **Phase 3**: Settings + plan gate + lifecycle + orchestrator (Phase 3.0-3.3)
- **Phase 4**: Provenance + trace + lessons + observability (Phase 4.0-4.3)
- **Phase 5**: AUTONOMOUS revision + events + 3 demos (Phase 5.0-5.5)
- **Phase 6**: Doc consolidation (in progress)

503 tests green, 35 commits, 4 detail whitepapers (STAR/LIFECYCLE/OBSERVABILITY/DEMOS), 11 stripped-down ARCHITEKTUR chapters.

### Open questions for implementation deep-dive

#### DoD engine

- **Threshold tuning**: global default `0.8`. Effector-specific? Learning over action history?
- **Source disable**: currently only via subset filter in the constructor. Sufficient or do we need a capabilities model?
- **Confidence aggregation**: currently sum-capped. Alternative: weighted mean by source reliability?
- **DoD caching**: cache per `(request_signature, context_signature)`?
- **Comparator extension**: currently Range/Threshold/Equality/Callable. Demand for set membership, regex?
- **DoD evolution across versions**: if the entity profile changes, the DoD changes. How do you compare "effector is at `fulfillment_score=0.85`" across DoD versions? Needs version-pair tracking, non-trivial.
- **Cross-tool DoD**: what is the DoD of a pipeline of 3 effectors? Aggregation of the individual DoDs, or a separate pipeline DoD? Ties to M4.
- **DoD conflicts between sources**: entity profile says `rooms_count=25..35`, RelatedEntities says `30..40`. Who wins? Today the hierarchy wins (step 1 before step 3). Always right?

#### DoD engine: Qualitative criteria — `evaluator` switch (Phase 7.1, implemented)

`Criterion.evaluator` selects the evaluation path per criterion. Three modes cover the practical spectrum:

```
rule         deterministic (Range / Threshold / Equality / Callable)
self_check   effector self-attests in the result dict
llm_judge    consumer callable evaluates
```

`llm_judge` is the most expensive mode; only use it where `rule` or `self_check` are not enough. Rule of thumb: one qualitative criterion per DoD is standard, three is a lot. Consumers inject the evaluation callables via `EvaluationContext(llm_judge=..., self_check=...)`. The Skelett itself has no LLM dependency.

Without a callable, `llm_judge` returns `(False, "no llm_judge callable configured")` — no silent pass.

#### DoD engine: Lesson distillation (Phase 7.2, implemented)

`_record_revision_lesson` now fills `criteria_hint` from `validation.unsatisfied` (instead of the earlier empty list). Per criterion:

```yaml
criteria_hint:
  - name: <failed criterion>
    expected: <original expected value>
    weight: <original weight * revision_lesson_weight_factor>   # default 0.5
    source: dod_failure
    evaluator: <preserved>
    revision_strategy: <preserved>
```

`LessonsSource` draws the criteria back into the DoD on the next `engine.derive()` — the loop closes. `OrchestratorSettings.lesson_context_keys` controls which ctx keys flow into the lesson's `context_pattern`; the default is an empty list, i.e. the lesson is matched context-free against the `kind`. Consumers override with e.g. `["domain", "subtype"]` for tighter match conditions.

#### Lifecycle

- **Per-kind transition policy**: currently global. Sensitive write operations may need more conservative thresholds.
- **Plan expiration**: time-based auto-expiry?
- **Score aggregation**: median instead of mean (more robust against outliers)?
- **Multi-stakeholder approve**: four-eyes principle as an extension?

#### Lifecycle: Granular revision modes per criterion (Phase 7.3, implemented)

`Criterion.revision_strategy` chooses, per criterion, the reaction to failure in AUTONOMOUS:

```
retry_alt_params      iterative retry up to autonomous_max_revision_attempts
                      (default — matches prior behavior)
escalate_to_human     lesson + plan-gate entry with failed_criteria,
                      ActionStatus.PROPOSED, no further retry
rollback_and_log      lesson + effector.rollback(action_descriptor, result)
                      (optional via hasattr — Effector protocol unchanged),
                      ActionStatus.DENIED
```

With multiple failed criteria the strictest strategy wins: `rollback > escalate > retry`. Per-action default via `OrchestratorSettings.default_revision_strategy`.

#### Operative defaults (Phase 7.4, implemented)

```
on_definition_unclear   ask | abort | proceed_with_warning
on_fulfillment_failed   warn | retry | abort
fulfillment_score_pass  0.0..1.0 (default 1.0 = strict; M5 recommendation 0.8)
```

With `fulfillment_score_pass=0.8`, an action with `validation.score >= 0.8` counts as fulfilled — even if weak criteria fall. `on_fulfillment_failed` applies in CHECKED/ROUTINE and in `apply_approved_plan` (AUTONOMOUS uses the revision strategies). Exposed via `ValidationResult.is_fulfilled(threshold)`.

#### Observability

- **Trace retention**: currently unlimited. Time-based cleanup?
- **Trace indexing**: with many traces `list()` becomes expensive as a linear scan.
- **Lessons lift tracking**: old-vs-new score comparison, promotion to DoD default.
- **EventBus persistence**: currently in-memory.
- **OTel span children**: currently flat. Hierarchical spans?
- **Provenance unification**: Plan/DoD/Lifecycle currently carry partial provenance — a later phase could unify them.

### Open questions for external consumers (Phase 7+)

- **Plan-gate UI**: web cockpit with a notification channel
- **Auto ToolRegistry registration**: effectors register via decorator
- **Real HTTP push** to Langfuse/Jaeger via OTel exporter
- **Self-improvement worker** in a real sandbox (E2B / Firecracker / container)
- **InsightService** for cross-effector queries
- **Karpathy loop** for autonomous few-shot generation

## 9. References

### Existing patterns the system adopts

- [Anthropic Agent Skills (December 2025)](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) — YAML frontmatter + Markdown body as the standard convention
- [OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) — provenance + span attributes
- [Levels of Autonomy for AI Agents (Knight Institute, arXiv 2506.12469)](https://arxiv.org/abs/2506.12469) — lifecycle stage vocabulary (per user role, the Skelett is per-action granular)
- [LangGraph `interrupt_on`](https://docs.langchain.com/oss/python/langchain/human-in-the-loop) — human-in-the-loop as a layer
- [Reflexion (Shinn et al., 2023, arXiv 2303.11366)](https://arxiv.org/pdf/2303.11366) — self-critique pattern (related to the `self_check` / `llm_judge` switch and to failure-lesson distillation in Phase 7.1/7.2)
- [Letta File-Memory Benchmark (2026)](https://www.letta.com/blog/benchmarking-ai-agent-memory) — empirical validation of file-first memory

### Novel contributions of the Skelett

- **Six-source DoD research hierarchy** with a global priority order — no published pattern has this in this form (Scrum.org "DoD for AI Agents" as the closest match at ~40%: a static DoD set, no research hierarchy).
- **Action lifecycle per action kind** with avg-score-driven stage transitions, sliding window, fresh start after transition. Knight 2506.12469 names this explicitly as "future work".
- **AUTONOMOUS revision loop** with lesson feedback in a closed loop.
- **Cross-domain verification as executable spec** (`tests/examples/test_cross_demo.py`).

### Reference implementation

Open-source Skelett: https://github.com/organism-core/organism-core

```bash
python -m examples.architect_lite    # Architecture practice demo
python -m examples.tax_lite          # Tax advisory demo
python -m examples.cfo_lite          # CFO office demo
pytest tests/                         # 503 tests green
```

---

**Closing image**

What stays constant at the bottom enables variation at the top. The domain is interchangeable, the five building blocks and five patterns are constant, the human stays at the center. M5 is the connecting joint that turns loose parts into an organism — a system that not only reacts but evaluates what it does.
