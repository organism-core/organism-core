# Production Default — Explicit Plan/HITL/Dispatch

> **Status:** Adoption lesson, decided 2026-06-09. Binding for
> production consumers; revises the implicit roadmap assumption that
> the autonomous reflex arc is the natural production endpoint.
> **Companion docs:** [`LIFECYCLE.md`](LIFECYCLE.md),
> [`STAR.md`](STAR.md), [`REENTRANCE.md`](REENTRANCE.md).

## 1. The lesson

The skeleton ships two ways to turn intent into effector action:

1. **The explicit pattern.** The consumer builds a structured plan
   with explicitly set DoD criteria, proposes it
   (`propose → Plan-Gate (HITL) → dispatch`), a human approves, the
   bridge executes against the external tool. The skeleton supplies
   the Plan-Gate, lifecycle states, EventBus, and validation; the
   consumer supplies the plan content.
2. **The autonomous reflex arc.** Raw input arrives without a stated
   goal; the system derives the DoD itself (`ActionOrchestrator` +
   DoD-engine derivation), and the effector fires once the derived
   criteria are satisfied. This is the "system infers what done
   means" vision.

The first real production consumer reached **all** of its live
outcomes through the explicit pattern. The reflex arc — although
fully present in the skeleton, tested, and demo-verified — was never
wired into a production path, and nothing was missed by its absence:
every workflow that mattered could state its goal explicitly at the
moment of proposing.

**Decision: the explicit Plan/HITL/Dispatch pattern is the
production default.** The autonomous reflex arc remains a
research/future track. It does not enter a production path until a
live use case demonstrates an outcome the explicit pattern cannot
deliver — the same evidence discipline that
[`REENTRANCE.md`](REENTRANCE.md) applies to mid-execution patterns.

## 2. Why

- **HITL safety is structural, not optional.** In the explicit
  pattern every side effect passes a human gate by construction.
  The reflex arc would make the gate conditional on derivation
  quality — a much harder thing to audit and a much easier thing to
  get silently wrong.
- **Provenance lives server-side at the effector target.** In
  production, the system of record that receives the write is where
  provenance fields persist. The explicit pattern composes cleanly
  with that: the plan carries the provenance payload, the target
  stores it. The reflex arc adds no provenance the explicit path
  does not already carry.
- **No missing outcome.** As of today there is no demonstrated
  production outcome that requires goal derivation from raw input.
  Where ambiguity exists, asking the user *before* proposing (the
  `clarification_needed` mechanism) has proven cheaper and safer
  than deriving and firing.

This holds across domains — the trenn-test passes trivially: a tax
practice approving postings, a CFO team approving forecast updates,
and a design office approving document writes all want the explicit
gate; none of them loses anything by deferring autonomous goal
derivation.

## 3. What this does NOT mean

- **The DoD engine is not demoted.** M5/DoD research
  (`engine.derive()`) stays the core of the skeleton — as a
  *research and derivation engine*: deriving acceptance criteria,
  scoring results, feeding validation and lessons. All of that is
  orthogonal to *who initiates the action*.
- **The reflex arc is not deleted.** `ActionOrchestrator` and the
  effector contract stay in the skeleton, tested, as the research
  track. The demos keep exercising them — that is what the demos
  are for.
- **No new abstraction is needed.** Consumers wire the explicit
  pattern out of existing parts (Plan-Gate, lifecycle, bridges).
  This memo changes the *default recommendation*, not the API.

## 4. Consequence for the roadmap

The M5/DoD engine keeps its place as the skeleton's centerpiece.
Its "effector-fires-itself" wiring — the step where a derived DoD
autonomously triggers `act()` in a production path — is **optional
and deferred**, behind an explicit trigger:

| Trigger | Condition | What changes |
|---|---|---|
| **0** | now — this memo | explicit pattern is the documented production default |
| **1** | a live use case appears where stating the goal explicitly is impossible or clearly inferior | scoped reflex-arc pilot behind the Plan-Gate (derivation proposes, human still approves) |
| **2** | the pilot shows outcomes the explicit pattern cannot match | full reflex-arc production wiring gets its own design review |

Until trigger 1, "wire the reflex arc into production" is not a
backlog item. It is a hypothesis waiting for evidence.

## 5. Summary

Production consumers should build on
`propose → Plan-Gate (HITL) → dispatch` with explicitly set DoD
criteria. The autonomous reflex arc stays a research track inside
the skeleton — alive in demos and tests, absent from production
paths, and re-promotable the moment a real outcome demands it.
