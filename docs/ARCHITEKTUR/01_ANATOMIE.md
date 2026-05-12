# 01 — Anatomie

> Welche Komponenten gibt es, was machen sie, wo leben sie?

## Übersicht

```
                  ┌─────────────────────────────────────────────┐
                  │      Z E N T R A L E S   S Y S T E M        │
                  │   EntityStore · DoDEngine · DoDValidator    │
                  │   PlanGate · LessonsAggregator · TraceStore │
                  │   LifecycleManager · EventBus · ToolRegistry│
                  └─────────────────────────────────────────────┘
                       ▲     ▲     ▲     ▲     ▲     ▲
                       │     │     │     │     │     │
   ┌──────────┬────────┴───┬─┴─────┴─┬───┴────┬┴─────┴──────────┐
   │          │            │         │        │                 │
┌──┴───┐  ┌───┴────┐  ┌────┴─────┐  ┌┴───┐  ┌─┴──────┐    ┌─────┴────┐
│      │  │        │  │          │  │    │  │        │    │          │
│ Eff  │  │ Eff    │  │ Eff      │  │Eff │  │ Eff    │ ...│ Eff      │
│  A   │  │  B     │  │  C       │  │ D  │  │  E     │    │  N       │
└──────┘  └────────┘  └──────────┘  └────┘  └────────┘    └──────────┘
```

Der Pfeil **nach oben** bedeutet: Effektor meldet seine Ergebnisse als Trace, Provenance-Eintrag, optional Lessons, optional Konflikte. Der Pfeil **nach unten** wäre: Zentrales System verteilt Master-Patterns, gepromotete Prompt-Varianten, Cross-Tool-Insights.

## Die Effektoren

Jeder Effektor hat **fünf Eigenschaften**, die ihn definieren:

- **Aufgabe** — was er erledigt
- **Sensoren** — wo er Daten liest
- **Effektoren-Output** — was er schreibt
- **Lebensraum** — wo der Code liegt
- **UI** — wie der User damit redet (oder kein-UI bei reinen Service-Effektoren)

## Effektor-Vertrag (5-Kontakt-Pattern)

Damit ein Effektor ins Framework passt, exposes er **fünf Kontaktstellen** (siehe [`08_GOLD_PATTERNS.md`](08_GOLD_PATTERNS.md) und [`src/organism/adapter/effector.py`](../../src/organism/adapter/effector.py)):

```python
class Effector(Protocol):
    name: str
    def pre_load(context) -> dict        # M1 Pre-Lookup
    def define_done(request, ctx) -> dict # M5 DoD
    def act(request) -> Any               # Aktion ausführen
    def upstream(kind, payload) -> None   # M2 Upstream-Pattern
    def gate(action) -> bool              # M3 User-Gate
```

`organism.adapter.BaseEffector` liefert sichere Default-No-Ops für alle fünf Kontaktstellen — Effektoren überschreiben nur was sie aktiv brauchen.

## Cross-Domain Effektor-Beispiele

Aus den drei Demo-Domänen:

| Demo | Effektor | Aufgabe | Sensoren | Output |
|---|---|---|---|---|
| `architect_lite` | `FloorPlanExtractor` | PDF-Pläne → Floor-Plan-Daten | PDF, Vision-API | `rooms_count`, `parking_as_single_room` |
| `tax_lite` | `TaxReturnValidator` | Steuererklärung prüfen | Mandanten-Steckbrief, Belege | `all_income_recorded`, `tax_class_in_range` |
| `cfo_lite` | `QuarterlyCloseRunner` | Quartals-Close ausführen | Reporting-Periode-Steckbrief | `cost_centers_closed`, `budget_variance` |

Identische 5-Kontakt-Effektor-Schnittstelle, unterschiedliche Domain-Logik. Siehe [`docs/DEMOS.de.md`](../DEMOS.de.md) für Details.

## Zentrales System

Aggregations-Schicht — kein Effektor, sondern Komponenten, die Effektoren orchestrieren oder ihren Output sammeln:

| Komponente | Modul | Aufgabe |
|---|---|---|
| EntityStore | `organism.memory` | YAML-Frontmatter + Markdown pro Entity |
| DoDEngine | `organism.dod` | Definition-of-Done aus 6 Quellen recherchieren |
| DoDValidator | `organism.dod` | Action-Result gegen DoD prüfen |
| PlanGate | `organism.plan_gate` | Approve/Reject-Cockpit für KI-Vorschläge |
| LifecycleManager | `organism.lifecycle` | State-Machine (a)→(e) pro action_kind |
| TraceStore | `organism.observability` | Audit-Record pro execute()-Aufruf |
| LessonsAggregator | `organism.lessons` | HITL-Korrekturen sammeln, Pattern-Promotion |
| EventBus | `organism.observability` | Pub/Sub für Cross-Component-Events |
| ToolRegistry | `organism.observability` | Capability-Discovery (welcher Effektor kann kind X?) |
| ActionOrchestrator | `organism.orchestrator` | Bindeglied zwischen allen oben |

Detail: [`02_NERVENSYSTEM.md`](02_NERVENSYSTEM.md), [`03_GEDAECHTNIS.md`](03_GEDAECHTNIS.md), [`docs/STAR.de.md`](../STAR.de.md), [`docs/LIFECYCLE.de.md`](../LIFECYCLE.de.md), [`docs/OBSERVABILITY.de.md`](../OBSERVABILITY.de.md).

## Was ein Effektor zur Integration braucht

Jeder Effektor sollte (oder sollte irgendwann) implementieren:

1. **5-Kontakt-Protokoll** — `Effector` Protocol oder `BaseEffector` Subklasse.
2. **Capabilities-Endpoint** — wenn als Service exponiert, listet Operationen mit JSON-Schema. Damit kann der ActionOrchestrator den Effektor abfragen, ohne den Code zu kennen.
3. **MCP-Adapter** (optional) — Effektor als MCP-Server registriert, damit externe Clients (z.B. andere LLMs) ihn nutzen können.
4. **A2A-Endpoint** (optional) — Effektor kann mit anderen Effektoren direkt sprechen.
5. **Provenance-Output** — jede KI-erzeugte Aussage hat `_provenance: {author, source, confidence, validated_by_user, timestamp}` als Marker.

Punkte 2-4 sind Phase-7+-Themen für externe Konsumenten (siehe [`10_LANDSCHAFT.md`](10_LANDSCHAFT.md)).

## Wo „Effektor" endet und „Service" anfängt

Faustregel:

- **Effektor** hat eine eigene Aktion mit Außenwirkung (`act()` ist nicht-trivial), läuft durch den ActionOrchestrator.
- **Service** ist eine Bibliothek oder Komponente des zentralen Systems, die mehrere Effektoren nutzen.

Beispiele:

- `EntityStore` — kein Effektor (kein User-Workflow). Wird von vielen Effektoren genutzt zum Steckbrief-Lookup.
- `LessonsAggregator` — Service. Aggregiert Lessons, wird vom Orchestrator und Effektoren befüllt.
- `DoDValidator` — Service. Prüft Action-Results gegen DoDs.

Im Zweifel: was eine eigene `act()`-Methode hat und durch `ActionOrchestrator.execute()` läuft, ist ein Effektor. Was nur API für andere Komponenten exposes, ist ein Service.

## Sub-Komponenten innerhalb eines Effektors

Effektoren sind oft mehrstufige Pipelines mit eigenen internen Services. Generisches Beispiel für einen Vision-basierten Extraktor:

```
Input (PDF/Image)
  └─ pre_processing_service       (Sanity-Check, Vorbereitung)
  └─ vision_service               (Vision-LLM-Call)
  └─ vector_service               (Strukturen extrahieren)
  └─ assembly_service             (Teil-Ergebnisse zusammensetzen)
  └─ master_anchor_service        (gegen Domain-Patterns abgleichen)
  └─ result_assembler             (Ergebnis-Dict zusammenstellen)
```

Diese internen Stufen sind **kein** Teil der Effektor-Anatomie für andere Effektoren — die sehen nur die `act(request)`-Schnittstelle. Aber wer am Effektor selbst arbeitet, muss die Pipeline kennen.

## Wann ein neuer Effektor dazukommt

Ein neuer Effektor braucht:

- 5-Kontakt-Protokoll-Implementation (oft via `BaseEffector` Subklasse)
- Action-Kind-Konvention (String-Konstante, z.B. `KIND = "extract_floor_plan"`)
- Provenance-Felder auf jedem Output (M2 Upstream-Pattern)
- Anschluss an Plan-Gate für nicht-trivial Schreibaktionen (M3 Gate-Pattern)
- Anschluss an LessonsAggregator für User-Korrekturen
- README oder docstring der die Effektor-Anatomie beschreibt

Siehe Demos in `examples/<demo>/effector.py` als Vorlage.
