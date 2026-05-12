*[🇬🇧 English version](LIFECYCLE.md)*

# LIFECYCLE — Plan-Gate, State-Machine, Orchestrator

> Konzept-Skizze als Whitepaper-Vorbereitung für Phase 6.
> Stand: 2026-05-09, nach Phase 3.3.

## Motivation

Eine Aktion wandert in einem lernenden System nicht in einem Sprung von „Mensch macht's manuell" zu „System macht's eigenständig". Sie reift in **fünf Stufen**, und jede Stufe hat einen anderen Mensch-System-Vertrag. Ohne diese Reife-Achse wandert ein System entweder zu schnell in Auto-Modus (und schreibt Mist) oder bleibt zu lange im Hand-Modus (und blockiert).

Das Lifecycle-Pattern macht die Reife **maschinen-bewertbar** — getrieben durch DoD-Erfüllungsraten aus dem [STAR](STAR.md)-Pattern. Es schließt damit die Lücke zwischen „abstrakte Reife" und „konkret messbarer Vertrauensgrad".

## Die fünf Stufen

```
   manuell ──→ vorgeschlagen ──→ geprüft ──→ routiniert ──→ eigenständig
    (a)            (b)             (c)           (d)            (e)
```

| Stufe | Wer prüft DoD | Konsequenz bei Verfehlung |
|---|---|---|
| (a) **MANUAL** | Mensch tut, kein DoD nötig | — |
| (b) **PROPOSED** | System schlägt vor + zeigt DoD | Plan-Gate-Eintrag enthält DoD |
| (c) **CHECKED** | System tut + checkt selbst | User-Hinweis statt stiller Fehler |
| (d) **ROUTINE** | System tut + Auto-Check | Drift triggert Rückfall nach (c) |
| (e) **AUTONOMOUS** | System tut + Auto-Check + Revision | Mensch nur bei Anomalie |

Stufen sind **per action_kind**, nicht per Effector — ein Effector kann mehrere Kinds bedienen, jeder mit eigener Reife. Der `action_kind` ist eine String-Konvention zwischen Effector und Caller (`"create_entity"`, `"update_field"`, `"send_notification"` etc.).

## Plan-Gate — die Stage-(b)-Mechanik

Stufe (b) ist **die einzige Stufe**, in der das Plan-Gate aktiv ist:

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

**Plan-Lebenszyklus**:
```
proposed ──approve──► approved ──apply──► applied
    │
    └──reject──► rejected
```

Jeder Übergang persistiert in `plans/{kind}/{plan_id}.yaml`. State-Übergänge sind strikt: `approve`/`reject` nur von `proposed`, `apply` nur von `approved` — sonst `ValueError`.

Plan-Daten:
- `id` (UUID4), `kind`, `payload`, `dod` (eingebettete DoD vom Vorschlagszeitpunkt)
- `proposed_by`, `proposed_at`
- `decided_by?`, `decided_at?`, `decision_reason`
- `applied_at?`

## Stage-Transitions

Promotion und Demotion werden durch **DoD-Erfüllungsraten über ein Sliding-Window** getrieben:

```
record_outcome(kind, plan_id?, score):
    state.recent_outcomes.append({plan_id, score, recorded_at})
    if len > window_size: trim
    transition = evaluate_transition(state)
    if transition:
        state.stage = transition.to_stage
        state.recent_outcomes = []           # Frischstart
        state.transition_history.append(transition)
    persist(state)
```

**Demotion-Check (Drift-Schutz, priorisiert)**:
- Falls die letzten `demote_after_n` Outcomes einen Durchschnitts-Score **unter** `demote_score_threshold` haben → eine Stufe zurück.

**Promotion-Check**:
- Falls die letzten `promote_after_n` Outcomes einen Durchschnitts-Score **mindestens** `promote_score_threshold` haben → eine Stufe weiter.

Demotion vor Promotion: ein System, das gerade abrutscht, soll nicht versehentlich befördert werden.

**Frischstart nach Transition**: `recent_outcomes` werden geleert. Verhindert Oszillation und gibt der neuen Stufe einen sauberen Bewertungszeitraum.

**Audit-Trail**: `transition_history` wird forever-archiviert. Jede Transition speichert `from_stage`, `to_stage`, `reason` (mit der konkreten Avg-Score-Berechnung), `transitioned_at`.

## ActionOrchestrator — das Bindeglied

```python
orchestrator = ActionOrchestrator(
    engine=DoDEngine(...),
    validator=DoDValidator(),
    plan_gate=PlanGate(...),
    lifecycle=LifecycleManager(...),
)

# Stage-abhängiger Routing-Aufruf:
result = orchestrator.execute(
    effector,
    kind="create_entity",
    request=...,
    context={...},
)

# Bei status=PROPOSED später:
orchestrator.apply_approved_plan(plan_id=result.plan.id, effector=effector)
```

`ActionResult.status` einer der:

| Status | Wann |
|---|---|
| `MANUAL` | Stage ist (a), System lehnt Automation ab |
| `PROPOSED` | Stage ist (b), Plan persistiert, Approval erwartet |
| `APPLIED` | Stages (c)/(d)/(e), Aktion lief, Validation enthalten |
| `DENIED` | `Effector.gate()` hat `False` zurückgegeben |
| `NEEDS_CLARIFICATION` | DoD enthält offene Klärungen — Aktion läuft nicht |

Zusätzliche Felder in `ActionResult`: `dod`, `plan?`, `result?`, `validation?`, `transition?`, `revision_pending`, `reason`.

## Stage-(e) AUTONOMOUS — Auto-Revision

In Stufe (e) führt das System die Aktion aus, validiert, und bei DoD-Verfehlung initiiert eine Revision. Phase 3.3 implementiert das als **Stub**: `revision_pending` wird auf `True` gesetzt, wenn `validation.all_satisfied is False`. Phase 4 verdrahtet die Lessons-Feedback-Schleife: Verfehlung → Lesson schreiben → DoD mit Lesson-Hint neu derive → erneuter `act()`-Versuch (mit Cap auf maximale Versuche).

Phase 3.3 dokumentiert die Lücke explizit, anstatt sie heimlich zu lassen.

## Settings

Alle konfigurierbaren Werte liegen in YAML unter `config/`, sind admin-UI-fähig (Settings-Registry):

| Component | Settings-Klasse | Felder |
|---|---|---|
| `PlanGate` | `PlanGateSettings` | `require_decision_reason: bool` |
| `LifecycleManager` | `LifecycleSettings` | `initial_stage`, `promote_after_n`, `promote_score_threshold`, `demote_after_n`, `demote_score_threshold`, `window_size` |

Per-Effector-Override für Lifecycle-Schwellen ist nicht in 3.x — wäre Phase 4+, falls Bedarf entsteht.

## Cross-Domain Beispielszenarien

Die State-Machine ist domänen-unabhängig. Beispiele über die drei Demo-Domains:

### architect_lite

```yaml
# lifecycle/extract_floor_plan.yaml
kind: extract_floor_plan
stage: checked
recent_outcomes:
  - plan_id: null
    score: 0.92
    recorded_at: '2026-05-09T10:00:00+00:00'
  # ... 28 weitere mit avg=0.93
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
  # ... 30 jüngste Buchungen mit avg=0.96
transition_history:
  - {from_stage: proposed, to_stage: checked, ...}
  - {from_stage: checked, to_stage: routine, ...}
```

### cfo_lite

```yaml
# lifecycle/run_close_step.yaml
kind: run_close_step
stage: proposed       # früh in der Reife — close steps sind heikel
recent_outcomes: []
transition_history: []
```

Identische State-Machine, identische Transition-Policy, gleiche YAML-Schema. Was nicht in allen drei Domains funktioniert, gehört nicht ins Skelett.

## Status & Offene Fragen

### Phase 3 Liefer-Stand (Stand 2026-05-09)

- 3.0 Settings-Infrastruktur (`SettingsBase`, Registry, Discovery)
- 3.1 PlanGate (Plan, PlanStore, Service mit propose/approve/reject/apply)
- 3.2 Lifecycle (Stages, State, Store, Manager, Drift-Detection)
- 3.3 ActionOrchestrator (Stage-Routing, apply_approved_plan-Flow)
- 277 Tests grün

### Phase 4+ ergänzt

- Lessons-Aggregator: Reject-Reasons + DoD-Failure-Reasons werden zu Pattern destilliert
- AUTONOMOUS-Revision: `revision_pending` wird mit Lesson-Feedback in act()-Retry verdrahtet
- Provenance-Schema in OTel-GenAI-Konvertierung
- Plan-Gate-UI als separates Konsumenten-Projekt (außerhalb des Skeletts)

### Offene Fragen für Phase 6 (Whitepaper-Konsolidierung)

- **Per-kind Transition-Policy**: aktuell global eine `LifecycleSettings`-Instanz. Sollten manche Kinds (heikle Schreibvorgänge) konservativere Schwellen haben?
- **Plan-Expiration**: Phase 3.1 hat `EXPIRED` im Enum, aber kein Auto-Expiry. Time-based Expiry (z.B. nach 7 Tagen)? Einheitliche Settings?
- **Concurrent Apply**: zwei Effectoren wenden parallel den selben Plan an — File-Lock? Optimistic Concurrency? Phase 4-Thema.
- **Revision-Cap**: bei AUTONOMOUS-Revision wie viele Versuche max? Lesson-Akkumulation pro Versuch?
- **Stage-Initial je kind**: aktuell ein globaler `initial_stage`. Operator-Wunsch: „heikle Kinds starten in MANUAL, sichere Lookups in CHECKED" — per-Kind-Override.
- **Window-Size**: 50 als globaler Default. Bei sehr seltenen Kinds (1× pro Woche) bräuchte man kürzere Fenster, bei häufigen längere.
- **Score-Aggregation**: aktuell arithmetisches Mittel. Alternativen: Median (robuster gegen Outlier), gewichteter Mittel mit Recency-Bias (jüngere Outcomes zählen mehr).
- **Multi-Stakeholder-Approve**: Plan-Gate hat einen `decided_by`. Multi-Approval (z.B. Vier-Augen-Prinzip) wäre Erweiterung — Phase 5+.
