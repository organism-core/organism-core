# 02 — Nervensystem

> Wie koordinieren die Effektoren? Was macht die Service-Schicht?

## Drei Ebenen Koordination

```
   User-Anfrage / externe Aktion / Event
              │
              ▼
   ┌────────────────────────────┐
   │  Reflex (synchron)         │   <-- Effektor ruft direkt Service auf
   │  z.B. EntityStore.read     │       Millisekunden, kein Approve nötig
   └────────────────────────────┘
              │
              ▼
   ┌────────────────────────────┐
   │  Insight (semi-async)      │   <-- 3-Stage PLAN/EXECUTE/AGGREGATE
   │  z.B. cross-effector Frage │       Sekunden, Effektor-Aufruf-Sequenz
   └────────────────────────────┘
              │
              ▼
   ┌────────────────────────────┐
   │  Plan (async, gated)       │   <-- KI schlägt vor, Mensch entscheidet
   │  z.B. Konflikt-Auflösung   │       Minuten-Stunden, Plan-Gate
   └────────────────────────────┘
              │
              ▼
   ┌────────────────────────────┐
   │  Lerntakt (background)     │   <-- Edits, Approves, Korrekturen werden
   │  z.B. Lesson-Aggregator    │       in Patterns destilliert
   └────────────────────────────┘
```

Jede Ebene hat einen anderen Zeitmaßstab und ein anderes Trust-Niveau. Effektoren dürfen **nur** auf Ebene 1+2 selbst handeln; alles auf Ebene 3 muss durch Plan-Gate.

## Reflex-Schicht

Synchrone Service-Calls. Antwort in <100ms. Effektor ruft auf, bekommt Antwort, macht weiter. Kein Plan-Gate.

| Service | Was es kann | Wer ruft auf |
|---|---|---|
| `EntityStore` | Entity-Steckbrief lookup, Liste aktiver Entities | jeder Effektor mit Entity-Kontext |
| `DoDValidator` | Action-Result gegen DoD prüfen | Orchestrator nach `act()` |
| `Provenance.now(...)` | Quellen-Wrapper für KI-Outputs | jeder Effektor, der schreibt |
| `ToolRegistry.find_for_kind(...)` | Capability-Lookup | Insight-Layer (Phase 5+ wired) |
| `EventBus.publish/subscribe` | Pub/Sub für lokale Events | Orchestrator, LessonsAggregator |

Diese Services sind **leichtgewichtig** und **deterministisch**. Sie führen keine LLM-Calls aus, treffen keine subjektiven Entscheidungen.

## Insight-Schicht

Cross-Effector-Orchestrierung. 3-Stage:

```
PLAN     → aus Anfrage Effektor-Aufruf-Sequenz erstellen
           (welche Effektoren, welche Parameter)
EXECUTE  → Effektoren sequenziell oder parallel rufen
           (mit Capabilities + MCP-Schema)
AGGREGATE → Antworten zusammenführen, Konflikte markieren,
            Quellen-Belegung erhalten
```

Realisiert als InsightService in einem Phase-7+-Konsumenten (außerhalb des Skeletts) — das Skelett liefert den `ToolRegistry`-Mechanismus, mit dem ein InsightService Capabilities discovern kann.

Was Insight gut kann:

- „Was sagt mir der Steckbrief, der letzte Trace UND die letzte Lesson zur Entity X?" — alle drei Quellen beigetragen, eine Antwort.

Was Insight nicht kann:

- Multi-Hop ohne explizite Capability-Liste („finde irgendwie raus ob X")
- Lernen aus eigenen Anfragen (jeder Aufruf startet bei null)

## Plan-Gate-Schicht

`organism.plan_gate.PlanGate` — die Bremse zwischen KI und Schreibaktion. Detail: [`docs/LIFECYCLE.de.md`](../LIFECYCLE.de.md).

Jede KI-Aktion in Lifecycle-Stage `(b) PROPOSED`, die in den Wahrheits-Speicher schreibt, muss:

1. `propose(kind=..., payload=..., dod=..., proposed_by=...)` aufrufen
2. Auf User-Approve warten (UI: extern, Skelett liefert nur API)
3. Bei Approve: `apply(plan_id)` ausführen
4. Bei Reject: Plan ablegen + optional Lesson schreiben („warum nicht")

Plan-Status:

- `PROPOSED` — vorgeschlagen, wartet auf Entscheidung
- `APPROVED` — User hat zugestimmt, kann appliziert werden
- `REJECTED` — User hat abgelehnt
- `APPLIED` — Aktion wurde ausgeführt
- `EXPIRED` — Auto-Expiry nach Timeout (Phase 6+ verdrahtet)

Plan-Gate ist **nicht optional** ab Stage `(b)`. Wer sich daran vorbeischreibt, hat einen Bug. Test: kann der User die Aktion rückgängig machen ohne git revert? Wenn nein → muss durchs Plan-Gate.

## Lerntakt-Schicht

Hintergrund-Threads, periodische Aggregation. Drei Pfade:

### Lessons-Aggregator

`organism.lessons.LessonsAggregator`. Sammelt User-Korrekturen aus allen Effektoren (z.B. via `record_lesson` oder Auto-Aufzeichnung im AUTONOMOUS-Revision-Loop des Orchestrators), gruppiert nach `(action_kind, context_pattern)`, leitet Hinweise an die DoD-Engine weiter über `LessonsSource`.

Phase-4-Stand: einfacher Log + Query. Pattern-Distillation, Lift-Tracking und Promotion-via-Plan-Gate (`kind=prompt_variant_promotion`) sind Phase 6+ Themen.

Detail: [`docs/OBSERVABILITY.de.md`](../OBSERVABILITY.de.md).

### Few-Shot-Loop

Periodisch:

- liest Failure-Cases aus TraceStore
- baut Few-Shot-Beispiele
- gibt sie dem nächsten LLM-Call als Kontext

Phase-7+-Thema (außerhalb des Skeletts), wird vom konsumierenden System realisiert.

### Self-Improvement-Loop

Sandbox-Worker (Phase 6+, siehe [`06_SELF_IMPROVEMENT.md`](06_SELF_IMPROVEMENT.md)):

- liest Capability-Lücken aus Trace + Insight
- schlägt Code-Änderung vor
- `propose(kind="code_patch")` → User-Approve

Heute: Konzept-Doku. Implementierung außerhalb des Skeletts.

## Wo das Nervensystem heute schwächelt

Stand des Skeletts (relativ zum Ziel-Bild):

1. **Insight-Layer ist nicht im Skelett**. Skelett liefert `ToolRegistry` als Discovery-Mechanismus, aber kein konkreter InsightService. Konsumenten implementieren ihn (Phase 7+).

2. **Plan-Gate-Promotion ist einseitig**. Lessons fließen vom Effektor nach oben (LessonsAggregator), aber zurück fließt heute manuell — ein Effektor muss aktiv die LessonsSource konsumieren via `LessonsAggregator.query_for_request()`. Phase-4-Stand: kein Auto-Pull beim Effektor-Start.

3. **EventBus ist underused**. Heute publiziert nur Orchestrator+LessonsAggregator. Konsumenten subscriben für eigene Cross-Component-Logik (Phase 7+).

Diese Schwächen sind nicht Bug, sondern **Wachstumsschwellen**. Sie werden in [`07_REIFEGRAD.md`](07_REIFEGRAD.md) als Roadmap-Items geführt.
