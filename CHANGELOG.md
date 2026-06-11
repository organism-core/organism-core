# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **⚠️ Alpha — breaking changes ahead.**
> Until `v1.0.0`, the public API (module paths, dataclass field names, YAML
> schemas in entity profiles and lifecycle state files) may change between
> minor versions. Pin to an exact version in production. The architectural
> patterns are stable; the surface that exposes them is still settling.

## [Unreleased]

(Nothing yet — first additions after `v0.1.0` go here.)

## [0.1.0] — 2026-05-12

First public release. Reference implementation of a quality-gated
multi-tool AI orchestration pattern. 712 tests green, three demo
domains verifying cross-domain genericity as an executable spec.

### Added

**Core building blocks**

- `organism.memory` — Entity memory pattern: one directory per entity
  containing `_entity_profile.md` (YAML frontmatter + free text). Schema-free.
- `organism.adapter` — Five-contact effector contract
  (`pre_load` / `define_done` / `act` / `upstream` / `gate`) via
  `Effector` Protocol, `BaseEffector` and `ReadEffector` base classes.
- `organism.query` — Two-contact querier contract (`query` / `cite`) +
  `QueryRunner` for the read-only path that skips DoD / plan-gate /
  lifecycle ceremony.
- `organism.dod` — **M5 DoD-Recherche engine** (the core). Six-source
  star hierarchy: `EntityFrontmatterSource` → `LessonsSource` →
  `RelatedEntitiesSource` → `VectorSearchSource` → `DomainPatternSource` →
  `UserClarificationSource`. Hybrid comparator (range / threshold /
  equality / callable). Validator with `ValidationResult` and weighted
  fulfillment score.
- `organism.settings` — YAML-round-trippable settings + admin-UI
  registry. Every component's defaults live in `config/<component>.yaml`.
- `organism.plan_gate` — Approve / reject service with file-backed plan
  persistence. Strict state transitions (`proposed → approved → applied`,
  or `proposed → rejected`).
- `organism.lifecycle` — Per-action-kind state machine
  `(a) MANUAL → (b) PROPOSED → (c) CHECKED → (d) ROUTINE → (e) AUTONOMOUS`
  with avg-score-driven transitions over a sliding window. Demotion
  prioritized over promotion. Fresh start after every transition.
- `organism.orchestrator` — `ActionOrchestrator` with stage routing,
  AUTONOMOUS revision loop, and `apply_approved_plan()` flow.

**Observability**

- `organism.provenance` — Shared `Provenance` container (author /
  timestamp / source / confidence / validated_by_user).
- `organism.observability` — `TraceStore` + `QueryTraceStore`,
  `EventBus` (in-memory pub/sub), `ToolRegistry` (capability discovery),
  OTel-GenAI semantic-conventions converter (structure-only, no SDK
  dependency), Langfuse adapter stub.
- `organism.lessons` — `LessonsAggregator` (record + query) and
  `LessonsSource` plugging back into the DoD engine. Closes the
  feedback loop from failed validations into future actions.

**UI layer**

- `organism.ui` — Headless Cockpit (the UI "Wesen"): hovers over
  orchestrator and stores, emits typed render schemas (`DoDView`,
  `PlanApprovalView`, `DriftView`, `QueryTraceView`) and a
  `UIEventStream` for any UI framework. `CockpitBuilder` for fluent
  assembly.

**M5-patch features** (Phase 7)

- Qualitative criteria via `Criterion.evaluator` switch
  (`rule` / `self_check` / `llm_judge`). No LLM dependency in the
  Skelett itself; consumers inject callables via `EvaluationContext`.
- Lesson distillation: `_record_revision_lesson` fills `criteria_hint`
  from `validation.unsatisfied`, closing the autonomous-revision loop
  through `LessonsSource`.
- Per-criterion revision strategies (`retry_alt_params` /
  `escalate_to_human` / `rollback_and_log`); strictest strategy wins
  on multi-criterion failure.
- Operative defaults: `on_definition_unclear`, `on_fulfillment_failed`,
  `fulfillment_score_pass`.

**Demos** (`examples/`)

- `architect_lite/` — architecture-practice domain
  (floor-plan extraction + lookup querier).
- `tax_lite/` — tax-advisory domain
  (tax-return validation + querier).
- `cfo_lite/` — CFO-office domain
  (quarterly close + cost-center querier).
- `full_recherche/` — shows the six-source DoD-Recherche hierarchy in
  full bloom with consumer-facing implementations of the three stub
  sources.
- `cockpit_demo/` — shows the Cockpit "Wesen" with all render schemas.

All three domain demos produce **identical pipeline counts** —
verified automatically by `tests/examples/test_cross_demo.py` as an
executable cross-domain genericity spec.

### Tests

- **712 tests green** at release.
- Two separation-test guards: `test_cross_demo.py` (action side) and
  `test_cross_demo_queries.py` (query side).
- `test_m5_features.py` guards the M5-patch per-domain features.

### Documentation

- Two-language convention: English primary (`*.md`), German
  counterpart (`*.de.md`) where applicable. See
  [`docs/TRANSLATION_GUIDE.md`](docs/TRANSLATION_GUIDE.md).
- Whitepapers in both languages:
  [`docs/M5_WHITEPAPER.md`](docs/M5_WHITEPAPER.md) /
  [`docs/STAR.md`](docs/STAR.md) /
  [`docs/LIFECYCLE.md`](docs/LIFECYCLE.md) /
  [`docs/OBSERVABILITY.md`](docs/OBSERVABILITY.md) /
  [`docs/DEMOS.md`](docs/DEMOS.md).
- Eleven German architecture chapters in
  [`docs/ARCHITEKTUR/`](docs/ARCHITEKTUR/) with an English chapter
  index at [`docs/ARCHITEKTUR/INDEX.en.md`](docs/ARCHITEKTUR/INDEX.en.md).
- Governance / separation contract in
  [`docs/STRATEGIE-EXTRACT.md`](docs/STRATEGIE-EXTRACT.md).

### License & contribution

- GNU AGPL-3.0, dual-licensed: free under the AGPL for everyone, with
  a commercial exception license available for closed-source / SaaS
  use (`info@brachia.dev`). The framework stays AGPL-3.0 and free.
  (Initial public releases up to and including v0.2.0 were published
  under Apache 2.0; from v0.3.0 onward the license is AGPL-3.0.)
- Contributor License Agreement: see [`CLA.md`](CLA.md). You keep
  copyright to your contribution; the project gets the rights needed
  to ship and re-license while always keeping at least one
  OSI-approved license open — which is what makes the dual-license
  possible.

### Known limitations (deliberate scope cuts for `v0.1.0`)

- No CI workflow shipped (`.github/workflows/` is empty). Tests are
  locally green; CI is a Phase-7+ topic for first adopters.
- `RelatedEntitiesSource`, `VectorSearchSource`, `DomainPatternSource`
  are stubs with stable APIs. Consumers wire real clients (vector
  store, pattern registry, similarity function).
- `LangfuseAdapter` is a stub (`posted_spans` for tests only); no real
  HTTP push.
- `EventBus` is in-memory; no cross-process persistence.
- Self-improvement worker: concept documented in
  [`docs/ARCHITEKTUR/06_SELF_IMPROVEMENT.md`](docs/ARCHITEKTUR/06_SELF_IMPROVEMENT.md);
  sandbox implementation (E2B / Firecracker / container) is consumer
  responsibility.
- Trace retention is unlimited (no time-based cleanup).

---

[Unreleased]: https://github.com/organism-core/organism-core/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/organism-core/organism-core/releases/tag/v0.1.0
