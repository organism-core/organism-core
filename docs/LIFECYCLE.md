*[🇩🇪 Deutsche Version](LIFECYCLE.de.md)*

# LIFECYCLE — Plan-Gate, State Machine, Orchestrator

> Concept sketch as whitepaper preparation for Phase 6.
> State: 2026-05-09, after Phase 3.3.

## Motivation

In a learning system an action does not jump in one step from "human does it manually" to "system does it autonomously". It matures in **five stages**, and each stage has a different human-system contract. Without this maturity axis a system either races into auto mode too fast (and writes garbage) or stays in hand mode too long (and blocks).

The lifecycle pattern makes maturity **machine-assessable** — driven by DoD fulfillment rates from the [STAR](STAR.md) pattern. It thereby closes the gap between "abstract maturity" and "concretely measured trust level".

## The five stages

```
   manual ──→ proposed ──→ checked ──→ routine ──→ autonomous
    (a)         (b)          (c)         (d)           (e)
```

| Stage | Who checks the DoD | Consequence on failure |
|---|---|---|
| (a) **MANUAL** | Human acts, no DoD needed | — |
| (b) **PROPOSED** | System proposes + shows DoD | Plan-gate entry contains the DoD |
| (c) **CHECKED** | System acts + checks itself | User notification instead of silent error |
| (d) **ROUTINE** | System acts + auto-check | Drift triggers fallback to (c) |
| (e) **AUTONOMOUS** | System acts + auto-check + revision | Human only on anomaly |

Stages are **per action_kind**, not per effector — one effector can serve several kinds, each with its own maturity. The `action_kind` is a string convention between effector and caller (`"create_entity"`, `"update_field"`, `"send_notification"`, etc.).

## Plan-Gate — the stage-(b) mechanic

Stage (b) is **the only stage** in which the plan gate is active:

```
                 ┌──────────────────────────────┐
                 │ ActionOrchestrator.execute() │
                 └──────────────┬───────────────┘
                                │
                ┌───────────────▼─────────────┐
                │ Lifecycle.get_stage(kind)   │
                └───────────────┬─────────────┘
                                │
              ┌─────────────────┼─────────────────────┐
              ▼                 ▼                     ▼
         (a) MANUAL      (b) PROPOSED          (c)/(d)/(e)
              │                 │                     │
        return MANUAL       PlanGate            Effector.act()
                            .propose()                │
                                │                     ▼
                          return PROPOSED       Validator.validate()
                                                      │
                                                      ▼
                                              Lifecycle.record_outcome()
                                                      │
                                                      ▼
                                              return APPLIED
```

**Plan lifecycle**:
```
proposed ──approve──► approved ──apply──► applied
    │
    └──reject──► rejected
```

Every transition is persisted in `plans/{kind}/{plan_id}.yaml`. State transitions are strict: `approve`/`reject` only from `proposed`, `apply` only from `approved` — otherwise `ValueError`.

Plan data:
- `id` (UUID4), `kind`, `payload`, `dod` (DoD embedded at the time of proposal)
- `proposed_by`, `proposed_at`
- `decided_by?`, `decided_at?`, `decision_reason`
- `applied_at?`

## Stage transitions

Promotion and demotion are driven by **DoD fulfillment rates over a sliding window**:

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

**Demotion check (drift protection, prioritized)**:
- If the last `demote_after_n` outcomes have an average score **below** `demote_score_threshold` → one stage back.

**Promotion check**:
- If the last `promote_after_n` outcomes have an average score **at least** `promote_score_threshold` → one stage up.

Demotion before promotion: a system that is currently slipping should not be inadvertently promoted.

**Fresh start after transition**: `recent_outcomes` is cleared. Prevents oscillation and gives the new stage a clean assessment window.

**Audit trail**: `transition_history` is archived forever. Each transition stores `from_stage`, `to_stage`, `reason` (with the concrete avg-score calculation), `transitioned_at`.

## ActionOrchestrator — the bridge

```python
orchestrator = ActionOrchestrator(
    engine=DoDEngine(...),
    validator=DoDValidator(),
    plan_gate=PlanGate(...),
    lifecycle=LifecycleManager(...),
)

# Stage-dependent routing call:
result = orchestrator.execute(
    effector,
    kind="create_entity",
    request=...,
    context={...},
)

# Later, when status=PROPOSED:
orchestrator.apply_approved_plan(plan_id=result.plan.id, effector=effector)
```

`ActionResult.status` is one of:

| Status | When |
|---|---|
| `MANUAL` | Stage is (a), system declines automation |
| `PROPOSED` | Stage is (b), plan persisted, approval expected |
| `APPLIED` | Stages (c)/(d)/(e), action ran, validation included |
| `DENIED` | `Effector.gate()` returned `False` |
| `NEEDS_CLARIFICATION` | DoD contains open clarifications — action does not run |

Additional fields in `ActionResult`: `dod`, `plan?`, `result?`, `validation?`, `transition?`, `revision_pending`, `reason`.

## Stage-(e) AUTONOMOUS — auto-revision

In stage (e) the system executes the action, validates, and on DoD failure initiates a revision. Phase 3.3 implements this as a **stub**: `revision_pending` is set to `True` when `validation.all_satisfied is False`. Phase 4 wires the lessons-feedback loop: failure → write lesson → re-derive DoD with lesson hint → another `act()` attempt (with a cap on maximum retries).

Phase 3.3 documents the gap explicitly instead of silently leaving it.

## Settings

All configurable values live in YAML under `config/`, are admin-UI capable (settings registry):

| Component | Settings class | Fields |
|---|---|---|
| `PlanGate` | `PlanGateSettings` | `require_decision_reason: bool` |
| `LifecycleManager` | `LifecycleSettings` | `initial_stage`, `promote_after_n`, `promote_score_threshold`, `demote_after_n`, `demote_score_threshold`, `window_size` |

Per-effector overrides for lifecycle thresholds are not in 3.x — would be Phase 4+, if demand arises.

## Cross-domain example scenarios

The state machine is domain-independent. Examples across the three demo domains:

### architect_lite

```yaml
# lifecycle/extract_floor_plan.yaml
kind: extract_floor_plan
stage: checked
recent_outcomes:
  - plan_id: null
    score: 0.92
    recorded_at: '2026-05-09T10:00:00+00:00'
  # ... 28 more with avg=0.93
last_transition_at: '2026-04-15T08:00:00+00:00'
transition_history:
  - from_stage: proposed
    to_stage: checked
    reason: 'promote: avg of last 30 = 0.91 >= 0.9'
    transitioned_at: '2026-04-15T08:00:00+00:00'
```

### tax_lite

```yaml
# lifecycle/post_buchung.yaml
kind: post_buchung
stage: routine
recent_outcomes:
  # ... 30 most recent bookings with avg=0.96
transition_history:
  - {from_stage: proposed, to_stage: checked, ...}
  - {from_stage: checked, to_stage: routine, ...}
```

### cfo_lite

```yaml
# lifecycle/run_close_step.yaml
kind: run_close_step
stage: proposed       # early in maturity — close steps are sensitive
recent_outcomes: []
transition_history: []
```

Identical state machine, identical transition policy, same YAML schema. Whatever does not work in all three domains does not belong in the Skelett.

## Status & open questions

### Phase 3 delivery state (as of 2026-05-09)

- 3.0 Settings infrastructure (`SettingsBase`, registry, discovery)
- 3.1 PlanGate (Plan, PlanStore, service with propose/approve/reject/apply)
- 3.2 Lifecycle (stages, state, store, manager, drift detection)
- 3.3 ActionOrchestrator (stage routing, apply_approved_plan flow)
- 277 tests green

### Added in Phase 4+

- Lessons aggregator: reject reasons + DoD failure reasons are distilled into patterns
- AUTONOMOUS revision: `revision_pending` is wired with lesson feedback into act() retry
- Provenance schema in OTel-GenAI conversion
- Plan-gate UI as a separate consumer project (outside the Skelett)

### Open questions for Phase 6 (whitepaper consolidation)

- **Per-kind transition policy**: currently a single global `LifecycleSettings` instance. Should some kinds (sensitive write operations) have more conservative thresholds?
- **Plan expiration**: Phase 3.1 has `EXPIRED` in the enum, but no auto-expiry. Time-based expiry (e.g. after 7 days)? Unified settings?
- **Concurrent apply**: two effectors apply the same plan in parallel — file lock? Optimistic concurrency? A Phase-4 topic.
- **Revision cap**: in AUTONOMOUS revision, how many attempts max? Lesson accumulation per attempt?
- **Initial stage per kind**: currently a global `initial_stage`. Operator request: "sensitive kinds start in MANUAL, safe lookups in CHECKED" — per-kind override.
- **Window size**: 50 as global default. For very rare kinds (once a week) you'd want shorter windows, for frequent ones longer.
- **Score aggregation**: currently arithmetic mean. Alternatives: median (more robust against outliers), weighted mean with recency bias (younger outcomes count more).
- **Multi-stakeholder approve**: plan gate has one `decided_by`. Multi-approval (e.g. four-eyes principle) would be an extension — Phase 5+.
