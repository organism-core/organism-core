# 04 — Lernen

> Wie verbessert sich das System über die Zeit?

## Drei Lern-Schleifen

```
   ┌─ Human-in-the-Loop ──────┐  ┌─ Few-Shot-Loop ──────┐  ┌─ Self-Improvement ──┐
   │  User korrigiert         │  │  KI lernt aus eigenen │  │  System schlägt sich │
   │  Effektor-Output         │  │  Failure-Cases (Few-  │  │  selbst Code-Fix vor │
   │  → Lesson                │  │  Shot)                │  │  → Plan-Gate         │
   └──────────────────────────┘  └───────────────────────┘  └──────────────────────┘
              │                            │                          │
              └────────────────────────────┴──────────────────────────┘
                                          ▼
                            ┌─ LessonsAggregator ─────┐
                            │  Sammelt, gruppiert,     │
                            │  promotet zu Pattern     │
                            └──────────────────────────┘
                                          │
                                          ▼
                            ┌─ Plan-Gate ──────────────┐
                            │  Mensch entscheidet bei  │
                            │  Promotion auf Default   │
                            └──────────────────────────┘
```

Die drei Schleifen laufen parallel mit unterschiedlicher Frequenz und Trust-Niveau. Sie speisen aber alle in den **LessonsAggregator** ein, der die zentrale Drehscheibe ist.

Phase-4-Stand: nur Schleife 1 (HITL) ist im Skelett implementiert. Schleifen 2+3 sind Konzept-Patterns für Phase 6+ und externe Konsumenten.

## Schleife 1: Human-in-the-Loop

**Frequenz**: bei jeder User-Interaktion mit einem Effektor-Output.
**Trust**: hoch (User ist Wahrheit).

Was eine Korrektur ist:

- User klickt „delete" auf einer Element-Card → der Effektor hat Element fälschlich erkannt
- User ändert Typ („Wand" → „Tür", „Kategorie A" → „Kategorie B") → Effektor hat falsch klassifiziert
- User editiert KI-Output und schickt ihn → ratio Original vs Edit unter 0.85 → Lesson „so wollte ich's nicht"
- User klickt „validiert" auf Provenance → KI-Fakt wird zur Wahrheit

Implementierung im Skelett (Phase 4.2):

```python
aggregator.record_lesson(
    kind="extract_floor_plan",
    observation="User korrigierte rooms_count von 7 auf 5",
    criteria_hint=[],
    confidence_delta=0.1,
    context_pattern={"floor": "basement"},
)
```

Lessons werden in `lessons/<kind>/<lesson_id>.yaml` persistiert. Detail: [`docs/OBSERVABILITY.de.md`](../OBSERVABILITY.de.md).

Konsumenten-Effektoren verdrahten User-Korrekturen über UI-Hooks → LessonsAggregator. Konkrete UI-Patterns sind Konsumenten-spezifisch.

**Phase-4-Stand des Pull-Pfads**: `LessonsSource` (Phase 4.2) wird vom DoD-Engine bei jedem `derive()` automatisch konsultiert. Lesson-Hints fließen damit in zukünftige DoD-Recherchen ein. Konkrete Lesson-Pattern-Distillation ist Phase-6+-Thema.

## Schleife 2: Few-Shot-Loop

**Frequenz**: periodisch (z.B. alle 5 Minuten oder nach N Failure-Cases).
**Trust**: mittel (KI lernt von KI, ohne User-Approve).

**Mechanik**:

1. Lese Failure-Cases aus TraceStore (was hat KI getan, was hat User korrigiert)
2. Baue für jeden Failure-Pattern ein Few-Shot-Beispiel
3. Hänge die Beispiele beim nächsten LLM-Call als Kontext an
4. Beobachte ob die Korrekturrate sinkt

Sicherheits-Caps üblich:

- max N Iterationen pro Run
- max M Tokens
- „leere Antwort"-Fallback (statt halluzinieren)

Was Few-Shot-Loop kann:

- Domain-spezifische Few-Shots an Vision-/Text-Effektoren
- Auto-Trigger bei Capability-Lücken-Cluster

Was er typischerweise nicht kann:

- Mehrere Effektoren übergreifend („ich habe in Effektor A gelernt, Effektor B profitiert") — das ist die EventBus + Cross-Tool-Lesson-Bus-Mechanik
- Persistente Few-Shots über Runs hinweg (Caching-Frage des Konsumenten)

Skelett-Stand: `TraceStore` (Phase 4.1) liefert die Failure-Cases als Datenquelle. Few-Shot-Builder ist Konsumenten-Verantwortung (Phase 7+).

## Schleife 3: Self-Improvement-Loop

**Frequenz**: opt-in, manuell oder bei Capability-Lücken-Cluster.
**Trust**: niedrig (Code-Änderung), darum durch Plan-Gate gesperrt.

Mechanik:

1. **Detect**: fehlende Capabilities clustern aus TraceStore + InsightService („ich brauchte X aber kein Effektor kann X")
2. **Worker**: in Sandbox läuft Few-Shot-Loop für Code-Vorschlag (max N Iter, max M Tokens, Sandbox-Fence)
3. **Propose**: `plan_gate.propose(kind="code_patch", payload=diff)`
4. **Gate**: User sieht Diff im Plan-Gate, approve/reject

Skelett-Stand: Konzept dokumentiert, Implementation außerhalb (siehe [`06_SELF_IMPROVEMENT.md`](06_SELF_IMPROVEMENT.md)).

## LessonsAggregator — die Drehscheibe

`organism.lessons.LessonsAggregator` (Phase 4.2). Detail: [`docs/OBSERVABILITY.de.md`](../OBSERVABILITY.de.md).

Was er aggregiert:

- alle 3 Schleifen oben (sofern Konsument sie verdrahtet)
- gruppiert nach `(action_kind, context_pattern)`
- berechnet Lift = (Korrektur-Erfolgsrate mit neuem Pattern) / (Korrektur-Erfolgsrate mit altem Pattern)

Lift-Tracking + Promotion-via-Plan-Gate (mit `kind="prompt_variant_promotion"` o.ä.) sind Phase-6+-Themen. Phase-4-Stand: einfacher Log + Query.

Wenn promoviert: ein generisches Variant-Switching-Pattern schaltet die neue Variante beim nächsten Effektor-Aufruf live.

## Cross-Effector-Lernen

Schwachstelle vieler Multi-Tool-Architekturen: Lesson aus Effektor A propagiert selten zu Effektor B.

Beispiele was fehlt (typisch):

- Rechnungs-Effektor lernt „diese Firma stellt immer überteuerte Rechnungen" — diese Information ist für Konversations-Effektor hilfreich, fließt aber nicht hin.
- Plan-Erkennungs-Effektor lernt „Klinik-Pläne haben ungewöhnliche Wand-Stärken" — Konversations-Effektor könnte beim nächsten Klinik-Vorgang direkt warnen.

Lösung im Skelett: **EventBus-basierter Cross-Effector-Channel** (Phase 5.1). Konsumenten subscriben:

```python
event_bus.subscribe("lesson_recorded", handler=propagate_to_other_effectors)
```

`handler` entscheidet welche Lessons für welche Effektoren relevant sind. Konkrete Filter-Logik ist domain-spezifisch.

## Compound Learning (das Hebel-Konzept)

Ein User-Click in einem Effektor-Output kann zu einem Master-Pattern werden, das **alle anderen ähnlichen Vorgänge** in Zukunft besser erkennen lässt.

Mechanik:

- User klickt „fehlendes Element hier hinzufügen" → `aggregator.record_lesson(...)` mit `criteria_hint=[Criterion(...)]`
- Bei nächster `engine.derive()` wird der Hint als Pattern-Source eingespeist (LessonsSource, Phase 4.2)
- Pattern matchen via `context_pattern` — automatisch in zukünftigen DoDs aktiv

Das ist die Schleife die das System **mit der Zeit besser** macht ohne dass am Effektor-Code etwas geändert wird (Erfolgs-Definition #1 aus [`00_LEITBILD.md`](00_LEITBILD.md)).

## Was getrackt wird (für Reinforcement-Signal)

Siehe [`06_SELF_IMPROVEMENT.md`](06_SELF_IMPROVEMENT.md). Kurz:

- TraceStore (was tat KI?)
- Plan-Gate-Decisions (was approves der User?)
- Edit-Ratios (wie stark verändert User KI-Output?)
- Reject-Reasons (warum lehnt User ab?)

Diese Signale füttern den Few-Shot-Loop und den Self-Improvement-Worker. Sie sind im Skelett primär lokal (`TraceStore`, `LessonsStore` — alle file-based). OTel-GenAI-Konvertierung ([`docs/OBSERVABILITY.de.md`](../OBSERVABILITY.de.md)) erlaubt späteren Export an externe Observability-Stacks.
