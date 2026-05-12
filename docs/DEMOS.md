*[🇩🇪 Deutsche Version](DEMOS.de.md)*

# DEMOS — Cross-Domain Genericity Validation

> Concept sketch as whitepaper preparation for Phase 6.
> State: 2026-05-09, after Phase 5.4.

## Motivation

Three demo domains implemented in parallel prove the central hypothesis of the repo:

> **The same pipeline codebase works in three different domains without modifying the orchestrator / engine / validator / plan-gate / lifecycle logic.**

If this hypothesis fails — for example because some pattern were architecture-practice-specific — that pattern does not belong in the Skelett. The demos are the litmus test.

## The three demos

| Demo | Domain | Action kind | Effector | Entities |
|---|---|---|---|---|
| `architect_lite` | Architecture practice | `extract_floor_plan` | `FloorPlanExtractor` | 3 floor plans (villa-alpha-basement, villa-alpha-ground, villa-beta-attic) |
| `tax_lite` | Tax advisory | `validate_tax_return` | `TaxReturnValidator` | 3 clients (client-042-2024, client-088-2024, gmbh-fischer-2024) |
| `cfo_lite` | CFO office | `run_close_step` | `QuarterlyCloseRunner` | 3 reporting periods (2024-Q3, 2024-Q4, 2025-Q1) |

All three domain datasets are **fictional** — no anonymization path from real data.

## Pipeline walk (identical across all three demos)

| Step | Stage | What happens |
|---|---|---|
| 1 | PROPOSED | Full propose → approve → apply sequence for one entity |
| 2 | CHECKED | 3 successful actions → lifecycle promotion to ROUTINE (`promote_after_n=3` for demo visibility) |
| 3 | AUTONOMOUS | Failing effector → revision loop (`autonomous_max_revision_attempts=2`), records lessons, gives up with `revision_pending=True` |
| 4 | (no run) | Manual HITL lesson via `aggregator.record_lesson()` |

## Separation-contract result

All three demos produce **identical pipeline counts**:

| Metric | architect_lite | tax_lite | cfo_lite |
|---|---|---|---|
| Entities seeded | 3 | 3 | 3 |
| Actions executed | 6 | 6 | 6 |
| Plans proposed | 1 | 1 | 1 |
| Plans applied | 1 | 1 | 1 |
| Traces recorded | 6 | 6 | 6 |
| Lessons recorded | 3 | 3 | 3 |
| Events captured | 11 | 11 | 11 |
| Transitions observed | 1 | 1 | 1 |
| Final stage | autonomous | autonomous | autonomous |

Event distribution (identical across all three):
- `plan_proposed`: 1
- `lifecycle_transition`: 1
- `trace_recorded`: 6
- `lesson_recorded`: 3

→ See `tests/examples/test_cross_demo.py` for the automated verification. If this test breaks, either the pipeline behaved domain-specifically (separation-contract violation) or one demo was changed inconsistently (should be kept parallel-consistent).

## Domain differences

What is unique to each demo (~100 lines of code per demo):

```
examples/<demo>/
  entities.py     Entity schema with frontmatter DoD criteria
  effector.py     Effector class with return_map (canned outputs)
  demo.py         Pipeline-walk prose (same 4-step structure,
                  only strings + KIND constant + decided_by name differ)
  README.md       Domain-specific instructions
```

What is shared (`src/organism/`, ~3000 lines):
- DoD engine + validator (Phase 2)
- PlanGate (Phase 3.1)
- LifecycleManager (Phase 3.2)
- ActionOrchestrator + AUTONOMOUS revision (Phase 3.3 + 5.0)
- Event wiring (Phase 5.1)
- Provenance + TraceStore + LessonsAggregator + EventBus + ToolRegistry + OTel converter + Langfuse stub (Phase 4)
- Settings layer (Phase 3.0)

**Ratio**: ~10% domain code, ~90% generic pipeline code. A fourth domain (e.g. `legal_lite`, `medical_lite`) would again be ~300 lines.

## Demo as a template for new consumers

Consumers wanting to integrate their own domain copy an existing demo:

```bash
cp -r examples/tax_lite examples/my_domain
```

Then adapt:
1. `entities.py` — entity schema with your own frontmatter DoD criteria
2. `effector.py` — `act()` with real logic (instead of return_map lookup); the other four contact points are often pre_load=identity, define_done={}, upstream/gate trivial
3. `demo.py` — KIND constant, possibly a few print strings, decided_by name
4. `__init__.py`, `__main__.py`, `README.md` — imports + instructions

The pipeline codebase (`src/organism/`) is **not touched**. Consumers extend via:
- Their own effectors (Phase 1.3 Protocol)
- Their own DoD sources (Phase 2.1 Protocol) if needed — the default six usually suffice
- Their own settings classes via `@register_settings(...)` if deployment-specific values are required

## Running them

```bash
python -m examples.architect_lite
python -m examples.tax_lite
python -m examples.cfo_lite
```

(from the repo root). Each demo uses a temporary directory (`tempfile.TemporaryDirectory()`), prints a complete pipeline walk to stdout, and cleans up at the end.

Library form for tests / consumer integration:

```python
from pathlib import Path
from examples.tax_lite import run_demo

summary = run_demo(Path("/tmp/my_run"))
print(summary.actions_executed)              # → 6
print(summary.event_types["lesson_recorded"]) # → 3
```

`run_demo(output_dir, print_fn=print)` optionally takes `print_fn` for quiet mode (tests pass `lambda x: None`).

## Output sample (architect_lite, shortened)

```
==============================================================
  architect_lite -- DoD pipeline walk
  3 synthetic entities, kind=extract_floor_plan
==============================================================

[SETUP]
  Stores in /tmp/architect_lite_xyz
  Engine: 6 sources (default), Threshold=0.5
  Lifecycle: initial=proposed, promote_after_n=3

[SEEDING]
  villa-alpha-basement (residential/basement, 2 criteria)
  villa-alpha-ground (residential/ground, 2 criteria)
  villa-beta-attic (residential/attic, 1 criterion)

[STEP 1] Stage PROPOSED -- propose -> approve -> apply
  execute() -> status=proposed, plan=35373c52...
  plan_gate.approve(...)
  apply_approved_plan() -> status=applied, score=1.00

[STEP 2] Stage CHECKED -- set_stage + 3 actions -> promotion
  villa-alpha-basement: status=applied, score=1.00
  villa-alpha-ground: status=applied, score=1.00
  villa-beta-attic: status=applied, score=1.00 -> TRANSITION checked -> routine
  Lifecycle after step 2: stage=routine

[STEP 3] Stage AUTONOMOUS -- failing effector -> revision loop
  execute() -> status=applied, score=0.00, revision_attempts=2, revision_pending=True
  -> 2 revision lessons recorded

[STEP 4] Manual HITL lesson
  aggregator.record_lesson(...)

[SUMMARY]
  Actions executed:       6
  Plans proposed:         1
  Traces recorded:        6
  Lessons recorded:       3
  Events captured:        11
  Final stage:            autonomous

  Event types:
    lesson_recorded: 3
    lifecycle_transition: 1
    plan_proposed: 1
    trace_recorded: 6
```

`tax_lite` and `cfo_lite` produce structurally identical output with domain-specific values.

## Status & open questions

### Phase 5 delivery state (as of 2026-05-09)

- 5.0 AUTONOMOUS revision loop (lesson feedback in orchestrator)
- 5.1 Event wiring (orchestrator + LessonsAggregator publish)
- 5.2 architect_lite demo
- 5.3 tax_lite demo
- 5.4 cfo_lite demo
- 5.5 docs/DEMOS.md + cross-demo verification test
- ~500 tests green

### Deliberately not in Phase 5

- **Plan-gate UI**: no web cockpit. Demos simulate approve directly via API.
- **Auto ToolRegistry registration**: effectors register manually (or not at all, as in the demos).
- **Real HTTP push to Langfuse**: the adapter is a stub, demos do not use it.
- **Karpathy loop / self-improvement loop**: Phase 6+ topics, or dropped.
- **Multi-step demos**: only 4 steps per demo. More complex workflows would be a per-consumer extension.

### Open questions for Phase 6 (whitepaper consolidation)

- **Stripping down `docs/ARCHITEKTUR/`**: currently domain-flavored from the predecessor. Phase 6 makes it generic.
- **Whitepapers for the public release**: merge STAR.md + LIFECYCLE.md + OBSERVABILITY.md + DEMOS.md or publish as modular whitepapers?
- **Demo as executable spec**: could the demos become CI smoke tests in Phase 6? (Today already via pytest tests, but CI setup is missing.)
- **CLI UX**: currently simple print. Phase 6+ maybe `rich` output for readability (terminal colors, tables)?
- **Demo sharing**: today the setup code is duplicated across 3 demos (~80 lines per demo). An `examples/_common/` helper would be DRY, but consumers would then have to copy+adapt first. Deliberate choice in Phase 5: duplication for template fitness. Phase 6 could reconsider.
- **Real effector logic**: today a deterministic return_map lookup. Consumers implement real effectors with vision-LLM calls / tax logic / close calculations.
- **Cross-demo tests in CI**: locally green today. Phase 6+ pipeline.
