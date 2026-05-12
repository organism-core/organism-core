*[🇩🇪 Deutsche Version](README.de.md)*

# organism-core

**Quality-gated multi-tool AI orchestration.**

Reference implementation that researches a Definition-of-Done before every action, validates the result against the derived criteria, and drives lifecycle stages from the score history.

**Status**: Phases 0-7 + Cockpit UI layer + Querier lineage.

## What is this?

An opinionated pattern set for systems where multiple AI tools work in parallel and consolidate their results into a central truth store. The Skelett ships generic building blocks (DoD engine, lifecycle state machine, plan gate, lessons aggregator, trace store, event bus, Cockpit). Consumers implement concrete effectors and queriers for their own domain.

## Why this exits?

Built at a working architecture practice with ~300 active projects. We needed an agent system that learns from corrections instead of repeating mistakes, and that earns autonomy instead of being granted it."

## What makes this different

Three primitives that the established multi-agent frameworks (LangGraph, CrewAI, AutoGen, Microsoft Agent Framework, AgentScope) do **not** expose as first-class:

1. **DoD-Recherche as pre-action research.** Before every action with external effect, the system researches the Definition of Done from six prioritized sources (entity profile, lessons, related entities, vector search, domain patterns, user clarification). Validates the result against the derived criteria after `act()`. Detail in [`docs/M5_WHITEPAPER.md`](docs/M5_WHITEPAPER.md).

2. **Cross-domain genericity as executable spec.** A CI test asserts that three demo domains (for example architecture, tax, CFO) produce identical pipeline counts. If a contribution accidentally makes the framework domain-specific, the test breaks. No other framework publishes this kind of automated genericity guard.

3. **Score-driven lifecycle stages.** Effectors promote `(a)→(b)→(c)→(d)→(e)` based on demonstrated quality (avg score over a rolling window) and demote on drift. Stages are not badges — they are earned and revoked automatically.

This is **complementary** to self-evolving agents (e.g. Hermes Agent) and to LLM-based reasoning agents — not in competition with them. organism-core provides the validation, lifecycle, and observability substrate; the reasoning agent runs on top.

Read-only tools have their own narrow lineage (`organism.query`) that skips the DoD / plan-gate / lifecycle ceremony — details in [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Quick start

```bash
git clone git@github.com:organism-core/organism-core.git
cd organism-core
pip install -e ".[dev]"

# Run one of the three demo domains (action side, pipeline walk):
python -m examples.architect_lite    # Architecture practice
python -m examples.tax_lite          # Tax advisory
python -m examples.cfo_lite          # CFO office

# Or see the DoD-Recherche traversal across all six sources:
python -m examples.full_recherche

# Or the headless UI "Wesen" (Cockpit) in action:
python -m examples.cockpit_demo

# Run the tests:
pytest tests/
```

The three domain demos print a complete pipeline walk to stdout
(setup → seeding → four steps: PROPOSED flow, CHECKED promotion,
AUTONOMOUS revision, HITL lesson). All three produce **identical
pipeline counts** — cross-domain verification as executable spec.

`full_recherche` is a fourth demo with a different focus: it shows
the **six-source hierarchy** of the DoD-Recherche engine (M5) in full
bloom, with minimal consumer-facing implementations of the three stub
sources (RelatedEntities / VectorSearch / DomainPattern) as templates.

`cockpit_demo` shows the headless UI Wesen — the Cockpit hovers over
the orchestrator and stores and emits typed render schemas (DoDView /
PlanApprovalView / DriftView / QueryTraceView) for any UI framework.

## Reading paths

| Who you are | Read |
|---|---|
| First overview | [`docs/M5_WHITEPAPER.md`](docs/M5_WHITEPAPER.md) (single document) |
| DoD engine in depth | [`docs/STAR.md`](docs/STAR.md) |
| Plan gate + lifecycle | [`docs/LIFECYCLE.md`](docs/LIFECYCLE.md) |
| Observability + lessons | [`docs/OBSERVABILITY.md`](docs/OBSERVABILITY.md) |
| Demos + genericity proof | [`docs/DEMOS.md`](docs/DEMOS.md) |
| Architecture concepts (German) | [`docs/ARCHITEKTUR/INDEX.en.md`](docs/ARCHITEKTUR/INDEX.en.md) (English chapter index) |
| Governance + separation contract | [`docs/STRATEGIE-EXTRACT.md`](docs/STRATEGIE-EXTRACT.md) |
| Two-language convention | [`docs/TRANSLATION_GUIDE.md`](docs/TRANSLATION_GUIDE.md) |

Doc index: [`docs/README.md`](docs/README.md).

## Modules

| Path | Job | Phase |
|---|---|---|
| `src/organism/memory/` | Entity memory (YAML+MD per entity), schema-free | ✅ 1 |
| `src/organism/adapter/` | Five-contact effector contract (Protocol + BaseEffector + ReadEffector) | ✅ 1 |
| `src/organism/query/` | Two-contact querier contract + QueryRunner (read-only path) | ✅ Q |
| `src/organism/dod/` | DoD-Recherche engine (star pattern, M5) — core | ✅ 2 |
| `src/organism/settings/` | YAML-round-trippable settings + admin-UI registry | ✅ 3 |
| `src/organism/plan_gate/` | Approve/reject service with file-backed plan persistence | ✅ 3 |
| `src/organism/lifecycle/` | State machine `(a)→(e)` with avg-score-driven transitions | ✅ 3 |
| `src/organism/orchestrator/` | ActionOrchestrator: stage routing + AUTONOMOUS revision loop | ✅ 3+5 |
| `src/organism/provenance/` | Provenance container (author / source / confidence / ...) | ✅ 4 |
| `src/organism/observability/` | TraceStore + QueryTraceStore, EventBus, ToolRegistry, OTel-GenAI converter, Langfuse stub | ✅ 4 |
| `src/organism/lessons/` | LessonsAggregator + LessonsSource | ✅ 4 |
| `src/organism/ui/` | Cockpit + render schemas + UIEventStream (headless UI layer) | ✅ UI |

## Demo domains

`examples/<demo>/` — parallel mini demos as a genericity discipline.
Whatever does not run in all three is too domain-specific:

- `examples/architect_lite/` — Architecture-practice-lite (floor-plan
  extraction effector + lookup querier)
- `examples/tax_lite/` — Tax-advisory-lite (tax-return validation +
  querier)
- `examples/cfo_lite/` — CFO-lite (quarterly close + cost-center
  querier)
- `examples/full_recherche/` — Shows the six-source DoD-Recherche
  hierarchy
- `examples/cockpit_demo/` — Shows the Cockpit Wesen with all render
  schemas

Each domain demo is self-contained (~300 lines) — usable as a
template for your own domain.

## Phase status

| Phase | Status | Content |
|---|---|---|
| 0 | ✅ | Repo init, empty module structure |
| 1 | ✅ | Memory + effector contract (BaseEffector + ReadEffector) |
| 2 | ✅ | DoD engine + six sources + validator |
| 3 | ✅ | Settings + PlanGate + Lifecycle + Orchestrator |
| 4 | ✅ | Provenance + trace + lessons + EventBus + OTel + Langfuse |
| 5 | ✅ | AUTONOMOUS revision + event wiring + three demos + cross-demo test |
| 6 | ✅ | Doc consolidation + M5 whitepaper + LICENSE + CI |
| 7 | ✅ | M5-patch code: evaluator switch + lesson loop + revision strategies + operative settings |
| UI | ✅ | Cockpit Wesen + render schemas + UIEventStream + CockpitBuilder |
| Q | ✅ | Querier lineage (read-only): protocol + runner + QueryTrace + Cockpit integration |

Per-phase detail in [`MEMORY.md`](MEMORY.md) (working journal, German).

## Test

```bash
pytest tests/
```

712 tests green. Two separation-test guards:
- `tests/examples/test_cross_demo.py` — Action side: all three domain
  demos produce identical pipeline counts.
- `tests/examples/test_cross_demo_queries.py` — Query side: all three
  domain queriers produce identical trace counts.

`tests/examples/test_m5_features.py` is the M5-patch-code guard for
the per-domain features (evaluator / revision strategies / operative
settings).

## License

Apache License 2.0 — see [`LICENSE`](LICENSE).

Contributions are accepted under the project's Contributor License
Agreement (see [`CLA.md`](CLA.md)). You keep copyright to your
contribution; you grant the project the rights needed to ship and
evolve it.

## Repository

https://github.com/organism-core/organism-core

---

*Human is curator, AI is proposal.*
