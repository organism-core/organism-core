*[🇩🇪 Deutsche Version](OBSERVABILITY.de.md)*

# OBSERVABILITY — Provenance, Trace, Lessons, Event Bus, OTel

> Concept sketch as whitepaper preparation for Phase 6.
> State: 2026-05-09, after Phase 4.3.

## Motivation

A learning system without observability ages like a tree without growth rings — it stands eventually, but nobody can trace how it got there. Observability captures **what was done, by whom, when, with what confidence, and with what outcome** — and makes that data available for three purposes:

1. **Audit** — humans want to retrace what happened (plan-gate decisions, DoD fulfillment rates)
2. **Learning** — the system learns from its own failure cases (lessons aggregator, Karpathy loop in Phase 6+)
3. **Tooling integration** — external observability stacks (Langfuse, Jaeger, OTel Collector) consume standardized spans

Phase 4 establishes the infrastructure. Phase 5+ wires it further; Phase 6 writes the public whitepaper.

## Architecture overview

```
┌────────────────┐
│ ActionOrchestrator         │
│ .execute() / .apply_*()    │
└────────┬───────────────────┘
         │
         ├──── records ────────► TraceStore       (audit trail per execution)
         │                              │
         │                              ▼
         │                       trace_to_otel_span()  (OTel-GenAI-conform JSON)
         │                              │
         │                              ▼
         │                       LangfuseAdapter / OTel exporter
         │
         ├──── reads ──────────► LessonsAggregator     (DoD feedback loop)
         │
         └──── publishes ──────► EventBus              (Phase 5+ subscribers)


  ToolRegistry  (capability discovery, Phase 5+ InsightService consumes)
```

## Provenance — who said what, when

`Provenance` is the shared audit container for AI assertions:

```python
@dataclass
class Provenance:
    author: str                  # effector name or "system"
    timestamp: datetime          # UTC ISO
    source: str = ""             # human-readable source (e.g. "orchestrator.execute")
    confidence: float = 1.0      # [0, 1]
    validated_by_user: bool = False
```

`Provenance.now(author, ...)` is the ergonomic factory with `datetime.now(utc)`.

Phase 4 uses Provenance in NEW types (Trace, Lesson, Event). Existing Phase 1+2+3 types keep their partial provenance (`Plan.proposed_by`, `DoD._provenance`, `LifecycleTransition.reason`) — Phase 6 unifies.

## Trace — audit record per action

Every `ActionOrchestrator.execute()` and `.apply_approved_plan()` call produces a trace, persisted in `traces/{trace_id}.yaml`:

```python
@dataclass
class Trace:
    id: str
    kind: str
    request_summary: str            # truncated repr
    context: dict[str, Any]         # post-pre_load context
    stage: LifecycleStage
    status: ActionStatus
    dod: DoD
    started_at: datetime
    completed_at: datetime
    provenance: Provenance
    # optional
    plan_id: str | None
    result_summary: str | None
    validation: ValidationResult | None
    transition_to: LifecycleStage | None
    revision_pending: bool
    reason: str
```

**TraceStoreSettings**:
- `enabled: bool = True` — overall recording on/off
- `summary_max_length: int = 500` — `request_summary`/`result_summary` truncation

Traces are recorded for **all** statuses (including MANUAL, NEEDS_CLARIFICATION, DENIED) — audit completeness.

## Lessons — human-in-the-loop feedback

`LessonsAggregator` is the hub of the learning loop:

```python
aggregator.record_lesson(
    kind="create_entity",
    observation="When entity_type=basement, expect 3-15 rooms",
    criteria_hint=[Criterion(name="rooms_count", expected="3..15")],
    confidence_delta=0.1,
    context_pattern={"entity_type": "basement"},
)
```

Storage: `lessons/{kind}/{lesson_id}.yaml`.

**Query mechanic** (called by LessonsSource):
```python
lessons = aggregator.query_for_request(
    kind="create_entity",
    context={"entity_type": "basement", "kind": "create_entity"},
)
# Filter: kind exact match, then context_pattern dict-equality match.
# Sort: newest first. Cap: query_max_results.
```

Match criterion for `context_pattern`: all keys/values from the pattern must be present exactly in the current context. Empty pattern → matches everything.

**LessonsSource** (priority 2 in the DoD star hierarchy) emits the `criteria_hint` of matching lessons as contributions into the running DoD. Confidence is summed and capped via `LessonsSourceSettings.max_confidence_delta` (default 0.5) — prevents a lessons flood from dominating early-stop.

**Phase-4 scope**: simple log + query. Lift tracking, pattern distillation, promotion-via-plan-gate (full description in `04_LERNEN.md`) are Phase 6+ topics.

## EventBus — in-memory pub/sub

Loosely-coupled cross-tool communication via typed events:

```python
@dataclass
class Event:
    type: str
    payload: dict[str, Any]
    timestamp: datetime
    provenance: Provenance | None = None
```

```python
bus = EventBus()
sub_id = bus.subscribe("trace_recorded", lambda e: print(e.payload))
bus.subscribe_all(lambda e: send_to_otel(e))      # wildcard

bus.publish(Event.now("trace_recorded", payload={"trace_id": "..."}))
bus.unsubscribe(sub_id)
```

**EventBusSettings**:
- `enabled: bool = True` — master switch
- `handler_error_action: "continue" | "raise"` — production default "continue" (handler exception swallowed; bus continues), test mode "raise" for strict error handling

Phase 4.3 provides the bus mechanism. **ActionOrchestrator does not publish yet** — a deliberate scope cut. Phase 5+ wires `trace_recorded`, `plan_proposed`, `lesson_recorded`, `lifecycle_transition` events.

## ToolRegistry — capability discovery

In-memory index, tools register on system start:

```python
registry.register(
    name="ef_create",
    kinds=["create_entity", "duplicate_entity"],
    description="Effector for entity creation",
)

# lookup
registry.find_for_kind("create_entity")  # -> [RegisteredTool, ...]
registry.get("ef_create")
registry.list()
```

A Phase 5+ InsightService would consume the registry ("which effector can serve kind=X?"). Phase 4.3 provides the data model; automatic registration is out of scope (effectors register manually).

## OTel-GenAI converter — structure-only

```python
span = trace_to_otel_span(trace)
# -> dict with gen_ai.* + organism.* attributes,
#    OTel-Semantic-Conventions-compliant JSON
```

**Attribute mapping**:

| OTel attribute | Source |
|---|---|
| `gen_ai.operation.name` | `trace.kind` |
| `gen_ai.system` | `trace.provenance.author` |
| `organism.lifecycle.stage` | `trace.stage.value` |
| `organism.action.status` | `trace.status.value` |
| `organism.dod.confidence` | `trace.dod.confidence` |
| `organism.dod.criteria_count` | `len(trace.dod.criteria)` |
| `organism.revision_pending` | `trace.revision_pending` |
| `organism.plan_id` | `trace.plan_id` (optional) |
| `organism.validation.score` | `trace.validation.score` (optional) |
| `organism.validation.all_satisfied` | `trace.validation.all_satisfied` (optional) |
| `organism.transition.to_stage` | `trace.transition_to.value` (optional) |
| `organism.reason` | `trace.reason` (optional) |

**Status mapping**:
- `OK` — APPLIED without validation, or with `all_satisfied=True`
- `ERROR` — APPLIED with a validation failure, or DENIED
- `UNSET` — PROPOSED, MANUAL, NEEDS_CLARIFICATION (the action did not run)

**Structural, no runtime dependency**: no `opentelemetry-api`/`opentelemetry-sdk` packages. The output is a dict that any OTel-compliant exporter (Jaeger, OpenTelemetry Collector, Langfuse) can consume. Consistent with the "Skelett-not-runtime" philosophy.

## Langfuse adapter

Stub for the Langfuse-specific push path:

```python
adapter = LangfuseAdapter(settings=LangfuseSettings(
    enabled=True,
    endpoint_url="https://cloud.langfuse.com",
    public_key="pk-...",
))
adapter.post_trace(trace)
```

**Phase 4.3 stub behavior**: keeps posted spans in `adapter.posted_spans` for tests. Phase 6+ replaces with a real HTTP push.

**LangfuseSettings**:
- `enabled: bool = False` — opt-in, default off
- `endpoint_url: str = ""`, `public_key: str = ""` — DEFAULT EMPTY. Real values belong in a deployment-specific override YAML (do NOT commit to the repo).

## Cross-domain example scenarios

Identical observability layer across all three demo domains:

### architect_lite

```yaml
# traces/abc-123.yaml
id: abc-123
kind: extract_floor_plan
status: applied
stage: routine
dod:
  criteria:
    - name: rooms_count
      expected: "3..15"
      source: entity_frontmatter
provenance:
  author: floor_plan_extractor
  source: orchestrator.execute
validation:
  all_satisfied: true
  score: 1.0

# lessons/extract_floor_plan/lesson-xyz.yaml
kind: extract_floor_plan
observation: "Basement plans often have parking-as-single-room"
context_pattern:
  floor: basement
criteria_hint:
  - name: parking_as_single_room
    expected: true
```

### tax_lite

```yaml
# traces/def-456.yaml
kind: post_buchung
status: proposed       # stage (b) — user must approve
stage: proposed
plan_id: plan-789

# lessons/post_buchung/lesson-uvw.yaml
kind: post_buchung
observation: "GmbH clients require ust_id check"
context_pattern:
  client_type: gmbh
criteria_hint:
  - name: ust_id_present
    expected: true
```

### cfo_lite

```yaml
# traces/ghi-789.yaml
kind: run_close_step
status: applied
stage: checked
validation:
  all_satisfied: false        # drift detected
  score: 0.6
revision_pending: false        # stage CHECKED, not AUTONOMOUS
reason: ""

# lessons/run_close_step/lesson-rst.yaml
kind: run_close_step
observation: "Q4 close needs reserve calculation"
context_pattern:
  quarter: 4
criteria_hint:
  - name: reserves_calculated
    expected: true
```

All three: identical YAML schema, identical TraceStore/LessonsStore layouts. Cross-domain examples are made visible in the documentation itself.

## Status & open questions

### Phase 4 delivery state (as of 2026-05-09)

- 4.0 Provenance datatype
- 4.1 Trace + TraceStore + orchestrator wiring
- 4.2 Lessons aggregator + LessonsSource full impl (replaces the Phase 2.3 stub)
- 4.3 EventBus + ToolRegistry + OTel-GenAI converter + Langfuse stub
- 469 tests green (state after 4.3)

### Added in Phase 5+

- ActionOrchestrator publishes events: `trace_recorded`, `plan_proposed`, `lesson_recorded`, `lifecycle_transition`
- Effectors register automatically in ToolRegistry on constructor invocation (or via a `default_sources` extension)
- AUTONOMOUS revision loop: on `revision_pending=True` the orchestrator pulls matching lessons + reruns `act()` with a lesson-extended DoD (capped at max-attempts)
- Demo CLI in `examples/{architect_lite,tax_lite,cfo_lite}/` shows trace+lesson+event output after every run

### Phase 6 (whitepaper consolidation) opens

- **Trace retention**: currently unlimited, file path grows. Time-based or count-based cleanup?
- **Trace indexing**: with many traces `list()` becomes expensive as a linear scan. SQLite index? Hash table?
- **Lessons lift tracking**: old-vs-new score comparison, promotion to DoD default (full `04_LERNEN.md` implementation)
- **EventBus persistence**: currently in-memory. Phase 5+ file-backed queue for cross-process subscriptions?
- **OTel span children**: currently flat. Hierarchical spans (parent_span_id) for sub-actions?
- **Tool capabilities schema**: currently a kinds list. Phase 5+ possibly structured capabilities with input/output schema?
- **Langfuse auth**: currently endpoint + public key. Phase 6+ with secret key, batched push, retry logic?
- **Provenance unification**: Plan/DoD/Lifecycle currently carry partial provenance. Phase 6 unifies on the `Provenance` container.
