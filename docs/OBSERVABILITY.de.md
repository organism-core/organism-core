*[🇬🇧 English version](OBSERVABILITY.md)*

# OBSERVABILITY — Provenance, Trace, Lessons, Event-Bus, OTel

> Konzept-Skizze als Whitepaper-Vorbereitung für Phase 6.
> Stand: 2026-05-09, nach Phase 4.3.

## Motivation

Ein lernendes System ohne Beobachtbarkeit altert wie ein Baum ohne Jahresringe — irgendwann steht er, aber niemand kann nachvollziehen, wie er dahin kam. Beobachtbarkeit erfasst **was getan wurde, von wem, wann, mit welcher Sicherheit, und mit welchem Ergebnis** — und macht diese Daten für drei Zwecke verfügbar:

1. **Audit** — Mensch will nachvollziehen, was passiert ist (Plan-Gate-Decisions, DoD-Erfüllungsraten)
2. **Lernen** — System lernt aus eigenen Failure-Cases (Lessons-Aggregator, Karpathy-Loop in Phase 6+)
3. **Tooling-Integration** — externe Observability-Stacks (Langfuse, Jaeger, OTel-Collector) konsumieren standardisierte Spans

Phase 4 etabliert die Infrastruktur. Phase 5+ verdrahtet sie weiter; Phase 6 schreibt das öffentliche Whitepaper.

## Architektur-Überblick

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
         │                       LangfuseAdapter / OTel-Exporter
         │
         ├──── reads ──────────► LessonsAggregator     (DoD-feedback loop)
         │
         └──── publishes ──────► EventBus              (Phase 5+ subscribers)


  ToolRegistry  (Capability-Discovery, Phase 5+ InsightService konsumiert)
```

## Provenance — wer hat was wann gesagt

`Provenance` ist der gemeinsame Audit-Container für KI-Aussagen:

```python
@dataclass
class Provenance:
    author: str                  # effector-name oder "system"
    timestamp: datetime          # UTC ISO
    source: str = ""             # human-readable Quelle (z.B. "orchestrator.execute")
    confidence: float = 1.0      # [0, 1]
    validated_by_user: bool = False
```

`Provenance.now(author, ...)` ist die ergonomische Factory mit `datetime.now(utc)`.

Phase 4 verwendet Provenance in NEUEN Typen (Trace, Lesson, Event). Bestehende Phase-1+2+3-Typen behalten ihre partielle Provenance (`Plan.proposed_by`, `DoD._provenance`, `LifecycleTransition.reason`) — Phase 6 unifiziert.

## Trace — Audit-Record pro Aktion

Jeder `ActionOrchestrator.execute()`- und `.apply_approved_plan()`-Aufruf erzeugt einen Trace, persistiert in `traces/{trace_id}.yaml`:

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
- `enabled: bool = True` — gesamtes Recording an/aus
- `summary_max_length: int = 500` — request_summary/result_summary-Truncation

Traces werden für **alle** Status erfasst (auch MANUAL, NEEDS_CLARIFICATION, DENIED) — Audit-Vollständigkeit.

## Lessons — Human-in-the-Loop-Feedback

`LessonsAggregator` ist die Drehscheibe der Lern-Schleife:

```python
aggregator.record_lesson(
    kind="create_entity",
    observation="When entity_type=basement, expect 3-15 rooms",
    criteria_hint=[Criterion(name="rooms_count", expected="3..15")],
    confidence_delta=0.1,
    context_pattern={"entity_type": "basement"},
)
```

Speicher: `lessons/{kind}/{lesson_id}.yaml`.

**Query-Mechanik** (LessonsSource ruft auf):
```python
lessons = aggregator.query_for_request(
    kind="create_entity",
    context={"entity_type": "basement", "kind": "create_entity"},
)
# Filter: kind exact match, dann context_pattern dict-equality match.
# Sort: newest first. Cap: query_max_results.
```

Match-Kriterium für `context_pattern`: alle keys/values aus dem Pattern müssen exakt im aktuellen context vorhanden sein. Empty pattern → matches alles.

**LessonsSource** (Priorität 2 in der DoD-Star-Hierarchie) emittiert die `criteria_hint` matchender Lessons als Beiträge in die laufende DoD. Confidence ist gesummt + via `LessonsSourceSettings.max_confidence_delta` (default 0.5) gecappt — verhindert Lessons-Flut, die den early-stop dominiert.

**Phase-4-Scope**: einfacher Log + Query. Lift-Tracking, Pattern-Distillation, Promotion-via-Plan-Gate (volle 04_LERNEN.md-Beschreibung) sind Phase 6+ Themen.

## EventBus — In-Memory Pub/Sub

Lose-gekoppelte Cross-Tool-Kommunikation über typed Events:

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
bus.subscribe_all(lambda e: send_to_otel(e))      # Wildcard

bus.publish(Event.now("trace_recorded", payload={"trace_id": "..."}))
bus.unsubscribe(sub_id)
```

**EventBusSettings**:
- `enabled: bool = True` — Master-switch
- `handler_error_action: "continue" | "raise"` — production-default „continue" (Handler-Exception swallowt; bus läuft weiter), Test-mode „raise" für strikte Fehlerbehandlung

Phase 4.3 stellt den Bus-Mechanismus bereit. **ActionOrchestrator publiziert heute noch nicht** — bewusster Scope-Schnitt. Phase 5+ verdrahtet `trace_recorded`, `plan_proposed`, `lesson_recorded`, `lifecycle_transition`-Events.

## ToolRegistry — Capability-Discovery

In-Memory-Index, Tools registrieren sich beim System-Start:

```python
registry.register(
    name="ef_create",
    kinds=["create_entity", "duplicate_entity"],
    description="Effector for entity creation",
)

# Lookup
registry.find_for_kind("create_entity")  # -> [RegisteredTool, ...]
registry.get("ef_create")
registry.list()
```

Phase 5+ InsightService würde Registry konsumieren („welcher Effector kann kind=X bedienen?"). Phase 4.3 stellt das Datenmodell bereit, automatische Registrierung ist nicht im Scope (Effectors registrieren sich manuell).

## OTel-GenAI-Converter — struktur-only

```python
span = trace_to_otel_span(trace)
# -> dict mit gen_ai.* + organism.* attributes,
#    OTel-Semantic-Conventions-konformes JSON
```

**Attribute-Mapping**:

| OTel-Attribut | Quelle |
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

**Status-Mapping**:
- `OK` — APPLIED ohne Validation oder mit `all_satisfied=True`
- `ERROR` — APPLIED mit Validation-Verfehlung, oder DENIED
- `UNSET` — PROPOSED, MANUAL, NEEDS_CLARIFICATION (Aktion lief gar nicht)

**Strukturell, keine Runtime-Dependency**: kein `opentelemetry-api`/`opentelemetry-sdk`-Pakete. Output ist ein dict, das jeder OTel-konforme Exporter (Jaeger, OpenTelemetry-Collector, Langfuse) konsumieren kann. Konsistent mit „Skelett-not-Runtime"-Philosophie.

## Langfuse-Adapter

Stub für Langfuse-spezifischen Push-Pfad:

```python
adapter = LangfuseAdapter(settings=LangfuseSettings(
    enabled=True,
    endpoint_url="https://cloud.langfuse.com",
    public_key="pk-...",
))
adapter.post_trace(trace)
```

**Phase-4.3-Stub-Verhalten**: hält gepostete Spans in `adapter.posted_spans` für Tests. Phase 6+ ersetzt mit echtem HTTP-Push.

**LangfuseSettings**:
- `enabled: bool = False` — opt-in, default off
- `endpoint_url: str = ""`, `public_key: str = ""` — DEFAULT LEER. Echte Werte gehören in deployment-spezifische Override-YAML (NICHT ins Repo committen).

## Cross-Domain Beispielszenarien

Identische Observability-Schicht über alle drei Demo-Domains:

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
status: proposed       # Stage (b) — User must approve
stage: proposed
plan_id: plan-789

# lessons/post_buchung/lesson-uvw.yaml
kind: post_buchung
observation: "GmbH-Mandanten benötigen ust_id-Check"
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
  all_satisfied: false        # Drift detected
  score: 0.6
revision_pending: false        # Stage CHECKED, not AUTONOMOUS
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

Alle drei: identisches YAML-Schema, identische TraceStore/LessonsStore-Layouts. Cross-Domain-Beispiele in der Doku selbst sichtbar gemacht.

## Status & Offene Fragen

### Phase 4 Liefer-Stand (Stand 2026-05-09)

- 4.0 Provenance datatype
- 4.1 Trace + TraceStore + Orchestrator-Wiring
- 4.2 Lessons-Aggregator + LessonsSource voll-Impl (replaces Phase-2.3-Stub)
- 4.3 EventBus + ToolRegistry + OTel-GenAI-Converter + Langfuse-Stub
- 469 Tests grün (Stand nach 4.3)

### Phase 5+ ergänzt

- ActionOrchestrator publiziert Events: `trace_recorded`, `plan_proposed`, `lesson_recorded`, `lifecycle_transition`
- Effectors registrieren sich automatisch in ToolRegistry beim Konstruktor-Aufruf (oder via `default_sources`-Erweiterung)
- AUTONOMOUS-Revision-Loop: bei `revision_pending=True` zieht der Orchestrator passende Lessons + reruns `act()` mit lesson-erweiterter DoD (Cap auf max-attempts)
- Demo-CLI in `examples/{architect_lite,tax_lite,cfo_lite}/` zeigt Trace+Lesson+Event-Outputs nach jedem Run

### Phase 6 (Whitepaper-Konsolidierung) öffnet

- **Trace-Retention**: aktuell unlimited, file-Pfad wächst. Time-based oder count-based Cleanup?
- **Trace-Indexing**: bei vielen Traces wird `list()` linear-scan teuer. SQLite-Index? Hash-table?
- **Lessons-Lift-Tracking**: alt-vs-neu Score-Vergleich, Promotion zu DoD-Default (volle 04_LERNEN.md-Implementation)
- **EventBus-Persistierung**: heute in-memory. Phase 5+ file-backed Queue für Cross-Process Subscription?
- **OTel-Span-Children**: heute flat. Hierarchische Spans (parent_span_id) für sub-aktionen?
- **Tool-Capabilities-Schema**: heute kinds-Liste. Phase 5+ vielleicht structured Capabilities mit input/output-Schema?
- **Langfuse-Auth**: aktuell endpoint+public-key. Phase 6+ mit secret-key, batched Push, retry-Logic?
- **Provenance-Unifikation**: Plan/DoD/Lifecycle haben heute partielle Provenance. Phase 6 unifiziert auf `Provenance`-Container.
