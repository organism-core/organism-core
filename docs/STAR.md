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
                  (6) UserClarification
                       (terminal)
```

The name "STAR" is a shape metaphor — not a specific algorithm from the literature. The radial structure is the central property: every source has equal weight _as a contribution_, but unequal weight _in order_. The engine evaluates in priority order `1→6` and stops early as soon as the DoD is clear.

## The six sources — hierarchy

| # | Source | What it contributes | Phase 2 |
|---|---|---|---|
| 1 | EntityFrontmatterSource | Declared DoD in the frontmatter of the referenced entity | full |
| 2 | LessonsSource | What was previously accepted as "done" (tool experience) | stub (Phase 4) |
| 3 | RelatedEntitiesSource | Cross-reference: similar entities with DoD hints | stub (Phase 5) |
| 4 | VectorSearchSource | Semantic search in a knowledge base (norms, standards) | stub (Phase 4) |
| 5 | DomainPatternSource | Domain standards and master patterns | stub (Phase 4) |
| 6 | UserClarificationSource | Terminal follow-up question when 1-5 are not enough | full |

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
- VectorSearchSource: wiring to vector-store client (Phase 4)
- DomainPatternSource: wiring to pattern registry (Phase 4)
- RelatedEntitiesSource: similarity function over `EntityStore` (Phase 5)
- Provenance schema in OTel-GenAI conversion (Phase 4)

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
