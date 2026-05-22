# Reentrance — Human Consultation Mid-Execution

> **Status:** Pattern reserved (Trigger 0). No code in the skeleton yet.
> **Companion docs:** [`STAR.md`](STAR.md), [`LIFECYCLE.md`](LIFECYCLE.md),
> [`M5_WHITEPAPER.md`](M5_WHITEPAPER.md).

## 1. Motivation

The skeleton today carries a clean sequence:

```
Event → Star research (DoD) → Plan PROPOSED → Plan-Gate (HITL)
       → dispatch → APPLIED / FAILED
```

That sequence is atomic from the Plan-Gate's point of view: once a
plan is `APPROVED`, the effector either succeeds (`APPLIED`) or
fails (`FAILED`). Nothing in between. No mid-execution interaction.

That was a deliberate starting point. Atomic plans gave the
skeleton a small surface to test and a clean audit story. But three
classes of real-world workflows do not fit:

- **Long-running jobs the user wants to abort.** A rendering plan
  takes five minutes. After two minutes the user notices the
  parameters were wrong and wants to cancel.
- **Mid-flight ambiguity discovered by the effector.** A long search
  effector finds three plausible match candidates instead of one.
  Guessing is worse than asking; the effector has no current way to
  ask.
- **Multi-step adjustments that branch on intermediate results.**
  A multi-step workflow is half-done when a value comes back unusual;
  the effector wants a yes/no from the user before committing the
  next step.

Today there is no plan status, no protocol surface, and no UI signal
for these cases. The first time a long-running workflow lands in
production, an ad-hoc workaround per effector is the path of least
resistance — and each ad-hoc workaround chips away at the
Plan-Gate's role as the single HITL contract. This memo reserves the
right pattern before that drift happens.

## 2. Four Design Options

| # | Option | Verdict |
|---|---|---|
| A | **Durable workflow engine** (Temporal, Restate, DBOS) | rejected: vendor lock-in, large operational footprint, undermines the "Plan-Gate is the contract" identity |
| B | **Question inbox separate from plans** (parallel queue, effector polls or is pinged) | rejected: two attention sinks for the user (plans + questions), cognitive load doubled |
| C | **Plan chunking** — break a long workflow into smaller plans with reviews between | rejected for this gap: solves *between-plan* coordination via `correlation_id`, but not *in-flight* cancel or in-flight clarification |
| **D** | **Parent-child plan reentrance** | chosen |

Option D keeps the Plan-Gate as the only HITL channel. A plan that
needs mid-execution input pauses itself and spawns a child plan whose
sole purpose is to capture the answer. The child goes through the
same propose/approve cycle every other plan goes through. No second
inbox, no external workflow engine, no audit-trail break — the
child's resolution is just another approve event.

## 3. Pattern Specification (Option D)

### 3.1 A new plan status: `PAUSED_AWAITING_INPUT`

It sits between `APPROVED` (the user has authorised the action) and
`APPLIED` (the action has actually been committed). State graph:

```
PROPOSED ──approve──► APPROVED ──dispatch──► (running)
                                              │
                                              ├──► APPLIED                    (today's happy path)
                                              ├──► FAILED                     (today's error path)
                                              ├──► CANCELLED                  (new, optional)
                                              └──► PAUSED_AWAITING_INPUT      (new)
                                                    │
                                                    └─child_resolved─► (running) ─► …
```

`PAUSED_AWAITING_INPUT` is a stable persisted state. A crash mid-pause
recovers cleanly: the plan YAML carries enough to resume.

### 3.2 New optional fields on the Plan dataclass

All three are optional and default to `None`. Atomic plans stay
unaffected.

```
parent_plan_id:       str | None    # this plan is a clarification child of …
spawned_child_plan_id: str | None   # this plan is paused waiting on …
resume_token:         str | None    # opaque token chosen by the effector,
                                    # supplied back to it on resume
```

### 3.3 Three optional effector protocols

Effectors that do not need reentrance keep the existing five-contact
contract. Three new protocols, all `runtime_checkable`, declare opt-in
capabilities:

```python
@dataclass
class RequiresInputResult:
    """Returned by Effector.act() instead of an ActionResult when the
    effector cannot proceed without a user decision."""
    question: str
    options: list[str] | None      # None => free-text answer
    resume_token: str              # opaque, effector owns the format
    rationale: str | None = None   # why is this needed

class SupportsResume(Protocol):
    def resume(
        self,
        resume_token: str,
        user_answer: str,
    ) -> ActionResult: ...

class SupportsCancel(Protocol):
    def cancel(self, resume_token: str) -> None: ...

class SupportsProgress(Protocol):
    def emit_progress(
        self,
        event_bus: EventBus,
        plan_id: str,
        step: int,
        total: int,
        msg: str,
    ) -> None: ...
```

A synchronous CRUD effector implements none of these and works
exactly as today. A renderer that needs cancel implements
`SupportsCancel` and `SupportsProgress`. A search effector that may
need a choice implements `SupportsResume` and returns
`RequiresInputResult` from `act()`.

### 3.4 Orchestrator behaviour on `RequiresInputResult`

1. The parent plan's status transitions to `PAUSED_AWAITING_INPUT`.
   `resume_token` is persisted in the plan YAML.
2. A child plan is created with `kind="clarification"` and the
   parent's id in `parent_plan_id`. Its DoD is small but real:
   - `Criterion(name="answer_not_empty", expected=True, weight=1.0)`
   - if `options` was supplied:
     `Criterion(name="answer_in_options", expected=True, weight=1.0)`
3. The child appears in the plan-gate as a normal `PROPOSED` plan.
   The UI surfaces it like any other.
4. On approve or reject the EventBus emits `child_plan_resolved`.
5. A wait-loop (poll every ~5 s, or an EventBus subscriber) sees the
   resolution and calls `effector.resume(resume_token, user_answer)`.
6. The effector returns either a regular `ActionResult` (done) or
   another `RequiresInputResult` (further clarification needed —
   another child plan, same pattern).
7. Final terminal state: `APPLIED`, `FAILED`, or `CANCELLED`.

### 3.5 Cancel as a special case

- A consumer-side endpoint exposes `cancel_plan(plan_id)`.
- The bridge calls `effector.cancel(resume_token)`. The effector is
  responsible for releasing whatever side-state it has (a background
  job, a temporary file, a network connection).
- Plan transitions to `CANCELLED`. No resume is possible after that.

### 3.6 Progress is orthogonal to reentrance

A progress emit does **not** change the plan status. The plan stays
`APPROVED`; the EventBus event `plan_progress` is purely a UI feed.
This is why `SupportsProgress` is its own protocol — a renderer can
emit progress without ever needing to pause.

## 4. EventBus Events

Four new events, all pub/sub, all consumer-readable:

| Event | Payload |
|---|---|
| `plan_progress` | `plan_id`, `step`, `total`, `msg` |
| `plan_paused` | `plan_id`, `child_plan_id`, `question` |
| `child_plan_resolved` | `parent_plan_id`, `child_plan_id`, `user_answer`, `decision` |
| `plan_cancelled` | `plan_id`, `by`, `reason` |

Consumers subscribe for UI rendering, lessons triggering, or
audit-log derivation. The skeleton stays passive — it publishes,
the consumer decides.

## 5. Out of Scope (Explicit)

The skeleton stays narrow on purpose. Four neighbouring patterns are
**not** in scope for this memo and not on the roadmap:

- **Multi-agent negotiation inside a single plan** (LangGraph /
  AutoGen-style multi-persona reasoning). Breaks cross-domain
  determinism and audit trail. The HITL channel is the only
  negotiation point we want.
- **Workflow engines with conditionals, loops, branches.** That
  belongs in the Glue-Strategy synthesiser (separate strand), not in
  the reentrance pattern. A `RequiresInputResult` is a single
  question, not an embedded program.
- **Durable process state via Temporal / Restate.** Plan YAML plus
  EventBus polling is enough for realistic single-server use. If a
  consumer ever needs horizontally-scalable durability, that is a
  later, separate sprint with its own justification.
- **Tree of plans (child spawns grandchild spawns …).** This memo
  reserves *one* level of hierarchy: parent + child. Deeper nesting
  is a state-machine explosion that has no real-world use case yet.
  When a real consumer wants it, we revisit.

## 6. Cross-Domain Evidence

The pattern needs to pass the trenn-test: it must work in all three
demo domains, not just one. Three concrete examples, one per domain:

- **`architect_lite`:** A rendering effector receives a request for
  a 3D view but cannot infer which viewpoint the user wants — front,
  side, isometric, or custom. `RequiresInputResult` with
  `options=["front", "side", "isometric", "custom"]`. The user picks
  via the child plan; the renderer resumes.
- **`tax_lite`:** A receipt-classification effector finds three
  plausible mandate assignments for the same receipt. Free-text
  clarification is fine here:
  `RequiresInputResult(options=None)`. The user types the mandate
  reference, the effector resumes and writes the assignment.
- **`cfo_lite`:** A long-running forecast simulation has been
  running two minutes. The user notices the input assumptions were
  off and triggers `cancel_plan`. The bridge calls
  `effector.cancel(resume_token)`; the effector terminates the
  simulation worker and releases the temp dataset.

Three different domains, three different shapes (options-list,
free-text, cancel-only), one pattern.

## 7. Implementation Triggers

This memo **does not** commit the skeleton to building anything. It
reserves the right path. Three staged triggers:

| Trigger | Condition | What gets built |
|---|---|---|
| **0** | now — this memo | nothing in code |
| **1** | first long-running workflow goes live (likely Render) | minimum-viable: `effector.cancel(resume_token)` + `emit_progress`. No `RequiresInputResult`, no parent-child plans yet. |
| **2** | second real use case with mid-flight clarification | full pattern: `RequiresInputResult` + parent-child plans + `PAUSED_AWAITING_INPUT` status + clarification-plan DoD shapes. |

Each trigger only ships what the live use case justifies. The next
trigger only ships when a second use case proves the pattern is not
a one-off shape.

## 8. UI Coupling

`PAUSED_AWAITING_INPUT` must be **prominently** visible. A status
that lives only in the plan-list panel is a missed opportunity — a
paused plan deserves a header-level signal so the user notices
without polling the inbox.

The header-halo indicator pattern (a glowing circle in a fixed
header slot, three states: still / soft-pulse / urgent-pulse) already
reserves an `urgent-pulse` state that points at
`PAUSED_AWAITING_INPUT`. When the reentrance pattern reaches trigger 1
or 2, the UI side will light up automatically — no new UI work
needed, the indicator is in place.

This memo notes the coupling explicitly so that future implementation
sprints inherit the convention: any new pause-style state should
target the urgent-pulse slot rather than invent a parallel UI signal.

## 9. Convergence — May 2026 industry signals

In the same week this memo was committed (2026-05-20), three
top-tier industry actors independently published designs that
target the same meta-problem: the monolithic request-response cycle
does not fit the reality of continuous user attention and ongoing
agent action.

**Anthropic Outcomes** (May 2026). Explicit success criteria
declared before an action runs; validation against those criteria
after the action returns. Architecturally adjacent to organism-core's
M5 DoD-research pattern; organism-core remains the provider-agnostic
open-source implementation.

**TML Interaction Models** (Thinking Machines Lab, research preview
2026-05-12). "Listen, speak, see and pause" trained into a single
network, not bolted on as an interaction wrapper. Full-duplex,
~0.4 s response latency. Solves the turn-taking limitation at the
**architecture layer** of the model itself.

**Google Android Halo** (2026-05-19, Google I/O). A persistent
status indicator surfacing what an AI agent is doing in real time —
an awareness layer for ongoing autonomous actions. Solves the
visibility-of-state limitation at the **OS layer**.

The reentrance pattern reserved here addresses the same meta-problem
at a third level: the **protocol layer**. `PAUSED_AWAITING_INPUT`
with parent-child plan reentrance, combined with EventBus progress
emissions, achieves the same kind of mid-execution human
consultation that TML achieves architecturally and Halo surfaces
visually — but in a deterministic, audit-traceable way that fits
multi-tool workflows with HITL discipline.

The three approaches do not compete; they layer.

| Layer | Example | What it solves |
|---|---|---|
| Architecture (model) | TML Interaction Models | mid-utterance bidirectional attention |
| Protocol (orchestration) | organism-core Reentrance | mid-execution human-in-the-loop with audit trail |
| UI (OS / app) | Android Halo | persistent visibility of agent state |

This convergence is treated as validation. Three independent actors
arriving at the same direction within a single week is signal, not
noise. The trigger conditions in Section 7 remain unchanged — the
convergence does not accelerate the build, but it does confirm the
design space is real.

Source pointers:

- Anthropic Outcomes — public beta announcement, May 2026
- TML Interaction Models research preview — Thinking Machines Lab,
  2026-05-12
- Google Android Halo — blog.google/products-and-platforms/platforms/android/android-halo/

## 10. Summary

Reentrance is not a feature today. The pattern is **reserved**, not
built. The skeleton ships the same atomic Plan-Gate contract it shipped
yesterday. When the first long-running workflow lives, the cancel and
progress story has a defined shape (trigger 1). When the second real
clarification case shows up, the full parent-child reentrance story
has a defined shape (trigger 2). Until then, the pattern sits in
`docs/REENTRANCE.md` as a discipline contract — and prevents ad-hoc
workarounds from accruing.
