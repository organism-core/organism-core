*[🇩🇪 Deutsche Version](STAR.de.md)*

# STAR — Definition-of-Done Research Engine

> Concept sketch as whitepaper preparation for Phase 6.
> State: 2026-05-09, after Phase 2.4.

## Motivation

In any multi-tool system with autonomous actors, an implicit gap arises: **what is a "correct" action?**

Classical success measures don't reach far enough:
- Tests pass → checks code correctness, not action correctness
- Human corrects afterwards → reactive, slow learning curve
- LLM confidence → self-referential, not calibrated

The **DoD pattern** (Definition of Done) closes this gap with a two-part rule:

> Before every action with external effect, the system **researches** the Definition of Done. If it cannot find a sufficiently clear DoD, it asks the user with targeted follow-up questions — before acting. **After** the action, it measures fulfillment of the DoD and writes the result back into memory.

The second sentence is the more important half. DoD is not just pre-research, but also post-assessment. Only the closed loop makes the system **evaluative** instead of merely reactive — and writing down failure lessons makes it **self-correcting**.

The DoD is not invented but researched from multiple sources, in a fixed order from _specific+concrete_ through _tried-and-true_ and _normative_ to _asking_.

### Two confidence quantities — please don't conflate

M5 distinguishes **two orthogonal** quantities, both of which are called "confidence/score":

- **Definition Confidence** (`DoD.confidence`, before `act()`) — how sure is the system that the DoD itself is well-formulated? Grows with each source contribution; sum-capped `[0,1]`. Drives early-stop.
- **Fulfillment Score** (`ValidationResult.score`, after `act()`) — how well was the DoD fulfilled? Weighted ratio of satisfied criteria. Drives lifecycle stage transitions.

A **well-defined DoD with high definition confidence** can have a **low fulfillment score** after the action — that is the normal case of a clearly recognized failure.

## The Star — Hub and Spoke

Six semantic sources lie radially around the action. The action is the center, each source a ray:

```
                     (1) EntityFrontmatter
                              │
        (2) Lessons ────┐     │     ┌──── (3) RelatedEntities
                        │     ▼     │           ├─ :prefix
                       ┌─────────────┐          └─ :tags
                       │  [ ACTION ] │
                       └─────────────┘
                        │     ▲     │
   (5) DomainPattern ───┘     │     └──── (4) VectorSearch
        ├─ :tuple             │
        └─ :action_only       │
                              │
                              ▼
                  (6) UserClarification
                       (terminal)
```

The name "STAR" is a shape metaphor — not a specific algorithm from the literature. The radial structure is the central property: every source has equal weight _as a contribution_, but unequal weight _in order_. The engine evaluates in priority order `1→6` and stops early as soon as the DoD is clear.

Two of the six sources — `RelatedEntitiesSource` and `DomainPatternSource` — ship as **two source instances each** in the default pipeline, so the engine writes separate provenance buckets per lookup heuristic (`:prefix`/`:tags`, `:tuple`/`:action_only`). Semantically still six sources; mechanically eight source instances. `default_sources()` returns eight in canonical order.

## The six sources — hierarchy

| # | Source | What it contributes | Status |
|---|---|---|---|
| 1 | EntityFrontmatterSource | Declared DoD in the frontmatter of the referenced entity | full |
| 2 | LessonsSource | What was previously accepted as "done" (tool experience) | full |
| 3 | RelatedEntitiesSource | Cross-reference: sibling entities discovered via prefix-cluster or tag-overlap heuristic | full (two instances) |
| 4 | VectorSearchSource | Semantic search via duck-typed chromadb-shaped client (chromadb not a dependency) | full |
| 5 | DomainPatternSource | Domain-specific canonical criteria from a consumer-supplied `PatternRegistry` | full (two instances) |
| 6 | UserClarificationSource | Terminal follow-up question when 1-5 are not enough | full |

Optional add-on sources (not part of `default_sources()`):
- `MarkdownRubricSource` — parses Anthropic-Outcomes Markdown rubric format directly into criteria. Drop-in interop.
- `CrossDomainLessonsSource` — re-injects lessons from other `kind`s when `match_keys` context overlaps. Reduced weight; cross-kind transfer is a secondary signal.

The order is domain-independent and reasoned:
- **Specific+concrete first** (Entity > Related > Vector > Pattern): whoever finds the answer in the concrete entity won't ask the vector store.
- **Tried-and-true before normative** (Lessons > Vector): tool-owned lessons beat normative texts because they are grounded in real practice.
- **Normative before asking** (1-5 > User): norms beat user questions because users don't want their time burned on things already known.

Reversing the order means asking the user things that are already in the frontmatter — that burns user trust.

The source order is **globally fixed**. Effectors pick a subset but don't reorder.

## Architecture

```
┌─────────────────┐
│   Effector      │   (five-contact adapter)
└────────┬────────┘
         │ define_done(request, ctx)
         ▼
┌─────────────────┐                   ┌──────────────────┐
│   DoDEngine     │ ──── call ─────► │  Source 1, 2, ... │
│   .derive()     │ ◄── contribute ── │                  │
│  (merge,        │                   └──────────────────┘
│   early-stop)   │
└────────┬────────┘
         │
         ▼
       DoD ─────────► act(request) ──────────► result
         │                                          │
         │                                          │
         └─────────► DoDValidator ◄─────────────────┘
                     .validate(dod, result)
                          ▼
                   ValidationResult
                   (score, all_satisfied, unsatisfied)
```

Engine + Validator are a pair:
- **Engine** defines: what should be fulfilled?
- **Validator** checks: what was fulfilled?

The gap between the two is the honest success metric.

### Data types (typed dataclasses)

```
Criterion           name, expected, weight, source
SourceContribution  source_name, criteria, confidence_delta,
                    clarifications, evidence
DoD                 criteria, clarification_needed, confidence,
                    evidence_sources, _provenance
                    .is_satisfied_for_act() :: bool

CriterionResult     name, satisfied, weight, expected, actual, reason
ValidationResult    criterion_results, score
                    .all_satisfied :: bool
                    .unsatisfied   :: list
```

All have `.to_dict()` for logging and later OTel-GenAI conversion (Phase 4).

### DoDSource protocol

```python
class DoDSource(Protocol):
    name: str
    def contribute(request, context, current) -> SourceContribution: ...
```

Structural subtyping (`runtime_checkable`) — no inheritance requirement, just the method signature. A class with the right attributes is a `DoDSource`, without explicitly inheriting.

## Engine algorithm

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
- _Criteria_: appended, stamped with `source` via `dataclasses.replace` (no mutation of source-internal state)
- _Confidence_: sum-capped to `[0, 1]`
- _Clarifications_: appended, order-preserving, no dedup
- _Provenance_: `source_name → list[criterion_name]`. Sources contributing only evidence (without criteria) are recorded with an empty list; silent sources (nothing at all) don't appear.

**Early-stop condition** is conjunctive:
- `confidence >= threshold` alone is NOT enough — if clarifications are open, continue
- `clarification_needed empty` alone is NOT enough — if confidence is low, continue

Otherwise subsequent sources can fill the clarification or raise the confidence. Default threshold: `0.8`, overridable per effector.

## Separator pattern — validator decoupled from effector

`DoDValidator` is its own component, not inlined in the effector. It sees only the `act()` result, not the implementation. When `evaluator=llm_judge`, the judging callable is itself a separate inference — so even the LLM reasoning is decoupled from the effector reasoning.

This is the same trust architecture Anthropic describes for their Outcomes feature as a "separate context window": a grader that does not know the implementation decisions cannot adapt its judgement to them. This separation is the architectural reason the validator lives outside the effector code — and why `llm_judge` takes an injected callable rather than hardcoding LLM routing in the validator.

## Parallel source dispatch — half the latency in production

The default engine runs the six sources sequentially. For real consumers with real source backends (vector DB call ~200 ms, pattern-registry API ~300 ms, related-entities scan ~100 ms), the latencies add up: ~700 ms just for pre-action research.

Optional `DoDEngine(parallel=True)` dispatches all sources concurrently via `ThreadPoolExecutor`:

```python
engine = DoDEngine(sources=[...], parallel=True, max_workers=6)
```

Latency becomes `max(source_latencies)` instead of `sum(source_latencies)` — typically 2-3× faster in production configurations.

Trade-offs (the engine surfaces them to the consumer rather than hiding them):
- **Early-exit is disabled** — all sources run, even when earlier sources already reach the confidence threshold. Negligible with cheap sources; for very expensive ones, prefer filtering sources upstream.
- **Source-level dedup is suppressed** — sources that dedupe against `current.criteria` (`LessonsSource`, `CrossDomainLessonsSource`, `MarkdownRubricSource`, ...) see an empty DoD and contribute their full lists. The engine dedupes post-hoc by `criterion.name`, **first-source-wins** in the original `sources` order.
- **Sources must be thread-safe** — all built-in sources are read-only on their backing stores. Custom sources must hold no mutable per-call state outside `contribute`.

Merge order remains deterministic via the `sources` list — a faster source can finish earlier but still appears at its configured position in the final DoD.

Source exceptions are isolated: a crashing source becomes `SourceContribution(evidence={"error": "<type>: <msg>"})`, other sources continue normally.

## Batched llm_judge — N-fold cost reduction

DoDs with multiple `evaluator=llm_judge` criteria pay one LLM call per criterion on the default path. In production workloads this is the single largest cost driver.

When the consumer sets a `batch_llm_judge` callable on `EvaluationContext`, the validator collects all eligible llm_judge criteria of a DoD and dispatches a **single batched call** instead of N separate ones. Signature:

```python
def batch_judge(criteria: list[Criterion], result: dict) -> dict[str, tuple[bool, str]]:
    """Returns name → (satisfied, reason) for each criterion in the batch."""
```

Eligibility rules (validator decides at runtime):
- `evaluator == llm_judge` (rule + self_check stay per-criterion)
- ≥ 2 eligible criteria (1 criterion → no batching benefit)
- The criterion key exists in the result (missing-key falls through cleanly to per-criterion)

On a batch exception or malformed response, each batched criterion fails with a clear reason (`batch evaluator error: ...`), never silently. Per-criterion fallback via the `llm_judge` callable stays available.

Performance promise: a DoD with 5 llm_judge criteria → 1 LLM call instead of 5.

## Comparator semantics (Validator)

Hybrid strategy to support both DoD definition paths (frontmatter-declared vs in-code):

| Form | Example | When | Meaning |
|---|---|---|---|
| `callable` | `lambda v: v > 0` | in-code DoDs | invoked, cast via `bool()` |
| `"lo..hi"` | `"25..35"` | YAML/frontmatter | inclusive numeric range |
| `">=N"` etc | `">=90%"`, `"<5"` | YAML/frontmatter | threshold (`>=`, `<=`, `>`, `<`), optional `%` suffix |
| anything | `True`, `42`, `"approved"`, `[1, 2]` | both paths | equality (`==`) |

**Conventions**:
- `%` suffix is stripped on both sides during parsing — user is responsible for a consistent scale (e.g. both sides `0..100` or both `0..1`).
- Booleans in numeric contexts are explicitly rejected (otherwise `True == 1` would skew range tests — Python `bool` is an int subclass). Boolean equality (expected=True, actual=True) continues to work via the equality path.
- Callable exceptions are caught, the criterion counts as unsatisfied with a reason text. Other criteria continue unaffected.
- Missing key vs explicit None is distinguished (reason vs equality check).
- String actuals are coerced via `float()` (with `%` stripped).

**Score** = `sum(weight if satisfied) / sum(all weights)`. Total weight = 0 yields `0.0` (no division by zero). Empty DoD: `score=0`, `all_satisfied=True` (vacuously).

## Lifecycle relationship

The action lifecycle stages become **machine-assessable only through DoD**:

| Stage | Who checks the DoD | Consequence on failure |
|---|---|---|
| (a) manual | Human acts, no DoD needed | — |
| (b) proposed | System proposes + shows DoD; human confirms | Plan-gate entry contains the DoD |
| (c) checked | System acts + checks itself against DoD; human validates | DoD failure: user notification instead of silent error |
| (d) routine | System acts + automatic DoD check; human spot-checks | Drift in DoD fulfillment rate triggers fallback to (c) |
| (e) autonomous | System acts + DoD check + revision on DoD failure | Human only on anomaly (DoD fulfillment < threshold) |

**DoD fulfillment rate over N actions** decides whether an action moves through (a)→(e) or back. Phase 3 (plan gate + lifecycle) consumes the validator outputs as a stage-transition signal.

## Example scenarios (cross-domain)

The three demo domains show identical engine logic with different content — the separation contract in action. All three use the same convention `frontmatter.dod.criteria`.

### architect_lite

```yaml
# examples/architect_lite/entities/villa-alpha/basement/_entity_profile.md
---
type: residential
floor: basement
dod:
  criteria:
    - name: rooms_count
      expected: "3..15"
      weight: 1.0
    - name: rooms_with_doors
      expected: ">=70%"
      weight: 0.8
    - name: parking_as_single_room
      expected: true
      weight: 0.5
---
```

### tax_lite

```yaml
# examples/tax_lite/entities/client-042/2024/_entity_profile.md
---
type: income_tax_return
fiscal_year: 2024
dod:
  criteria:
    - name: all_income_recorded
      expected: true
      weight: 1.0
    - name: deductions_plausible
      expected: ">=0"
      weight: 0.7
    - name: tax_class_in_valid_range
      expected: "1..6"
      weight: 1.0
---
```

### cfo_lite

```yaml
# examples/cfo_lite/entities/2024-Q3/_entity_profile.md
---
type: quarterly_close
fiscal_year: 2024
quarter: 3
dod:
  criteria:
    - name: cost_centers_closed
      expected: true
      weight: 1.0
    - name: provisions_updated
      expected: true
      weight: 0.9
    - name: budget_variance
      expected: "-0.05..0.05"
      weight: 0.5
---
```

All three domains: identical engine, identical validator, same convention. Whatever does not run in all three is too domain-specific and does not belong in the Skelett.

## Status & open questions

### Phase 2 delivery state (as of 2026-05-09)

- DoDEngine complete (Phase 2.1)
- EntityFrontmatterSource full (Phase 2.2)
- 4 stub sources with stable API (Phase 2.3)
- DoDValidator with hybrid comparator (Phase 2.4)
- 144 tests green

### Added in Phase 4+

- LessonsSource: wiring to lesson aggregator (Phase 4)
- Provenance schema in OTel-GenAI conversion (Phase 4)

### Three external-backend sources made real (Stub→Real)

What were stubs through Phase 5 are now full implementations. Each leans on an injectable backend so `organism-core` stays dependency-free:

- **RelatedEntitiesSource** — prefix-cluster heuristic (`343_alpha` finds `343_beta`) and tag-overlap heuristic (frontmatter `tags` intersection). Ships as **two source instances**, each with its own provenance bucket (`related_entities:prefix`, `related_entities:tags`). Re-injected criteria carry reduced weight via `cross_entity_weight_factor` (default 0.5).
- **DomainPatternSource** — `PatternRegistry` keyed by `(action_type, entity_type)`. Two source instances (`domain_pattern:tuple`, `domain_pattern:action_only`) for separate provenance tracks. `organism-core` ships only the registry interface; the domain knowledge lives in the consumer's setup.
- **VectorSearchSource** — duck-typed chromadb-shaped adapter (chromadb is **not** a dependency). Generic `default_query_builder` prioritises universal text fields (`text`/`description`/`name`/`title`/`summary`) plus `entity_id`/`kind` from context. V1 contributes one `similar_cases_present` criterion plus confidence proportional to hit count (capped); aggregate hit-metadata stats is V2.

`default_sources()` therefore returns 8 source instances in canonical order, not 6. The semantic count remains 6 sources; the two-instance pattern is purely a provenance-routing detail.

### Phase 8 — Outcomes interop + cross-domain transfer

- **REVISION_OUTCOME_FAILED (8A)** — terminal outcome distinct from EXHAUSTED. Raised when DoD re-derivation in the revision loop surfaces fresh `clarification_needed` — the rubric itself is incoherent with the request, not just out of attempts. Mirrors Anthropic Outcomes' `failed` vs `max_iterations_reached` distinction.
- **MarkdownRubricSource (8B)** — parses Anthropic-Outcomes Markdown rubric format (`## section` + `- bullet` + optional `[weight=N]`) into `Criterion` objects. Drop-in interop for consumers who already maintain rubrics in that format. Bullets default to `evaluator=llm_judge`.
- **CrossDomainLessonsSource (8C)** — pulls lessons recorded under *other* `kind`s when `match_keys` context dimensions overlap. Same engine, run inline at DoD-derive time. Reduced weight factor on re-injected criteria (`cross_kind_weight_factor`, default 0.3) — cross-kind transfer is a secondary hint, never decisive.

### Lesson-pile observability sensor (mini-P3, implemented)

Before building a lesson-distillation worker speculatively, surface the symptom and wait for it to show up in production:

`LessonsAggregator.usage_stats()` returns `age_days_p95`, `recent_use_ratio`, `never_used_count` per kind. `Cockpit.summary()` surfaces them on `EffectorSummaryView`. Window is configurable via `CockpitSettings.lessons_recent_use_window_seconds` (default 7d). `_last_used` is in-memory only — this is a sensor, not an audit log.

Trigger heuristic for building the distillation worker: watch for rising `lessons_count` plus rising `age_days_p95` plus falling `recent_use_ratio` — the pile-up signal. Build only when the sensor reports it in real production.

### When DoD research is dispensable

Sharper heuristic than "read vs write" (a vector search is a read but has success criteria):

- **Dispensable** for **deterministic** operations (SQL lookup, file read, exact schema match)
- **Dispensable** in stage `(a) MANUAL`
- **Required** for **probabilistic** operations, including reads (vector-search ranking, classification, OCR, AI-driven extraction)
- **Required** from stage `(b) PROPOSED` onward
- **Required** for every write action into the truth store

### Open questions for Phase 6 (whitepaper consolidation)

- **Threshold tuning**: global default `0.8` — but when is that right? Effector-specific? Learning over action history?
- **Source disable per effector**: currently only via subset filter in the constructor. Sufficient or do we need a capabilities model?
- **Confidence aggregation**: currently sum-capped. Alternative: weighted mean by source reliability?
- **DoD caching**: cache per `(request_signature, context_signature)`? Phase 4 plays this through.
- **Language**: this document was German originally. Public release in Phase 6 calls for an English version or bilingual.
- **Comparator extension**: currently range, threshold, equality, callable. Demand for set membership (`expected = ["a", "b"]` as "in"), regex (`expected = "^foo.*"`)?
- **Weighted vs strict score**: currently weighted ratio. Alternative: strict (all satisfied = `1.0`, otherwise `0`)?
- **Negative confidence**: today floored at `0.0`, protecting against source mistrust. Use case for negative contributions (source actively contradicts)?
- **DoD evolution across entity-profile versions**: if the frontmatter changes, the DoD changes. How do you compare `fulfillment_score` across DoD versions?
- **Cross-tool DoD**: pipeline of 3 effectors — aggregation of the individual DoDs or a separate pipeline DoD?
- **DoD conflicts between sources**: entity profile says `25..35`, RelatedEntities says `30..40`. Today the hierarchy wins (step 1 before 3). Always right?

### Qualitative criteria — `evaluator` switch (Phase 7.1, implemented)

`Criterion.evaluator` selects the evaluation path:

```
rule         deterministic (Range / Threshold / Equality / Callable)
self_check   effector self-attests in the result dict
llm_judge    consumer callable evaluates (Skelett ships no LLM lib)
```

`llm_judge` is the most expensive mode; only use it where `rule` or `self_check` are not enough. Rule of thumb: one qualitative criterion per DoD is standard, three is a lot.

Consumers inject the evaluation callables via `EvaluationContext(llm_judge=..., self_check=...)`. Without a callable, `llm_judge` returns `(False, "no llm_judge callable configured")` — no silent pass.

### Granular revision modes per criterion (Phase 7.3, implemented)

`Criterion.revision_strategy` chooses, per criterion, the reaction to failure in AUTONOMOUS:

```
retry_alt_params      current behavior (default) — iterative retry up to
                      autonomous_max_revision_attempts
escalate_to_human     lesson + plan-gate entry with failed_criteria —
                      ActionStatus.PROPOSED, no retry
rollback_and_log      lesson + effector.rollback(descriptor, result) (optional
                      via hasattr) — ActionStatus.DENIED
```

With multiple failed criteria the strictest strategy wins: `rollback > escalate > retry`. Default strategy via `OrchestratorSettings.default_revision_strategy`.

### Lesson distillation from DoD failure (Phase 7.2, implemented)

`_record_revision_lesson` fills `criteria_hint` from `validation.unsatisfied`. Weight per criterion is reduced to `revision_lesson_weight_factor` times the original (default 0.5); `source` is set to `"dod_failure"`; `evaluator` and `revision_strategy` are preserved. `LessonsSource` pulls the criteria back into the DoD on the next `engine.derive()` — the loop closes.

`OrchestratorSettings.lesson_context_keys` controls which context keys flow into the lesson's `context_pattern` (default: empty = context-free match on `kind`).

### Operative defaults (Phase 7.4, implemented)

```
on_definition_unclear   ask | abort | proceed_with_warning   (default ask)
on_fulfillment_failed   warn | retry | abort                 (default warn)
fulfillment_score_pass  0.0..1.0                             (default 1.0)
```

With `fulfillment_score_pass=0.8` (M5-patch recommendation), an action with `validation.score >= 0.8` counts as fulfilled — even if weak criteria fall. With default `1.0` the semantic is strict (equivalent to `all_satisfied`). `on_fulfillment_failed` applies in CHECKED/ROUTINE and in `apply_approved_plan`; AUTONOMOUS uses the revision strategies.
