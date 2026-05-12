# 07 — Reifegrad

> Wie wird Reife pro Effektor und pro action_kind gemessen?

## Zwei Ebenen Reife

Das Skelett unterscheidet zwei orthogonale Reife-Achsen:

1. **Implementations-Reife pro Effektor** — wie viele der verbindlichen Patterns (P1-P10 aus [`05_REFLEXBOGEN.md`](05_REFLEXBOGEN.md)) hält der Effektor ein?
2. **Vertrauens-Reife pro action_kind** — wie weit ist diese Aktion im Lifecycle (a)→(e) (siehe [`09_FRAMEWORK.md`](09_FRAMEWORK.md), [`docs/LIFECYCLE.de.md`](../LIFECYCLE.de.md))?

Beide sind getrennt zu bewerten. Ein technisch perfekt implementierter Effektor (Achse 1: alle Patterns ✓) startet trotzdem in Stage `(b) PROPOSED` (Achse 2: noch kein Vertrauen). Umgekehrt kann ein älterer Effektor in `(d) ROUTINE` sein, obwohl ihm noch P9 (Health-Endpoint) fehlt.

## Achse 1: Implementations-Reife (5 Bewertungs-Achsen)

Statt einer Pauschal-Prozent-Angabe „Effektor X ist 90% reif", werden **fünf konkrete Achsen** geprüft. Jede ist binär (✓/✗) oder dreistufig (vollständig/partiell/fehlt).

### A1 — Pre-Lookup-Pflicht (P1)

Liest der Effektor `entity_id` aus `context` und ruft `EntityStore.read()` auf, bevor `act()` läuft?

- ✓ Vollständig: ja, immer wenn `entity_id` bekannt
- ◐ Partiell: nur in einigen Pfaden
- ✗ Fehlt: nein, blind

### A2 — Provenance-Coverage (P3)

Trägt jeder schreibbare Output einen `_provenance`-Block (`organism.provenance.Provenance`)?

- ✓ Vollständig: alle Outputs
- ◐ Partiell: nur einige (z.B. nur die Strukturierten, nicht die Freitexte)
- ✗ Fehlt: kein Provenance

### A3 — Lesson-Hook (P8)

Schreibt der Effektor bei jeder User-Korrektur eine Lesson via `LessonsAggregator.record_lesson()`?

- ✓ Vollständig: jede Korrektur-Surface ist verdrahtet
- ◐ Partiell: einige Korrektur-Surfaces ohne Hook
- ✗ Fehlt: keine Lessons aufgezeichnet

### A4 — Plan-Gate-Anbindung (P4)

Werden nicht-triviale Schreibvorgänge über `PlanGate.propose()` geleitet (oder über den ActionOrchestrator, der das automatisch handhabt)?

- ✓ Vollständig: alle Schreibvorgänge ab Stage `(b)` durch Gate
- ◐ Partiell: einige direkte Schreib-Bypässe
- ✗ Fehlt: schreibt direkt ohne Gate

### A5 — Capabilities-Discovery (P7)

Ist der Effektor in `ToolRegistry` registriert mit klaren `kinds` und Description?

- ✓ Vollständig: registriert + dokumentiert
- ◐ Partiell: registriert ohne Description, oder nur in Code-Konstante
- ✗ Fehlt: nicht registriert

### Bewertungs-Tabelle (Vorlage)

| Effektor | A1 Pre-Load | A2 Provenance | A3 Lesson-Hook | A4 Plan-Gate | A5 Capabilities | Σ |
|---|---|---|---|---|---|---|
| `<my_effector>` | ✓/◐/✗ | ✓/◐/✗ | ✓/◐/✗ | ✓/◐/✗ | ✓/◐/✗ | N/5 |

Mindestanspruch: **3/5 ✓**, mit A1 (Pre-Lookup) und A4 (Plan-Gate) als Pflicht-Achsen. Norm: **4-5/5**.

## Achse 2: Vertrauens-Reife (Lifecycle Stage)

Pro `action_kind` (nicht pro Effektor — ein Effektor kann mehrere kinds bedienen):

| Stage | Bedeutung | Wer prüft DoD | Vertrauen |
|---|---|---|---|
| `(a) MANUAL` | Mensch tut, KI sieht zu | — | n/a |
| `(b) PROPOSED` | KI schlägt vor + zeigt DoD; Mensch entscheidet | Plan-Gate-Eintrag | niedrig |
| `(c) CHECKED` | KI tut + checkt selbst gegen DoD | nachträgliche User-Validation | mittel |
| `(d) ROUTINE` | KI tut + Auto-Check; Mensch stichprobenhaft | Drift triggert Rückfall | hoch |
| `(e) AUTONOMOUS` | KI tut + Auto-Check + Revision | nur bei Anomalie | sehr hoch |

Stage-Übergänge sind **avg-Score-getrieben** (siehe [`docs/LIFECYCLE.de.md`](../LIFECYCLE.de.md)):

- Promote: avg(letzte `promote_after_n` Outcomes) ≥ `promote_score_threshold` → eine Stufe weiter
- Demote: avg(letzte `demote_after_n` Outcomes) < `demote_score_threshold` → eine Stufe zurück

Defaults: `promote_after_n=30`, `score≥0.9`; `demote_after_n=5`, `score<0.7` (`LifecycleSettings`, Phase 3.2).

## Sichtbarkeit

Pro Effektor sollte das Repo eine Reifegrad-Tabelle pflegen — z.B. in `<consumer>/REIFEGRAD.md` oder in einem zentralen Dashboard. Konkrete UI-Implementation ist Konsumenten-Aufgabe (Phase 7+).

Datenquellen für die Tabelle:

- `LifecycleStore.list_kinds()` für Stage pro kind
- `ToolRegistry.list()` für registrierte Effektoren
- Code-Inspektion oder Pattern-Tests für Achse-1-Bewertung

## Roadmap-Priorisierung über Reifegrad

Die Tabelle aus Achse 1 zeigt direkt **wo investiert werden soll**:

- Mehrere Effektoren mit ✗ in derselben Achse → systemisches Loch (z.B. Lesson-Hook fehlt überall → LessonsAggregator-Onboarding-Sprint)
- Ein Effektor mit ✗ in mehreren Achsen → Effektor-Reifegrad-Initiative (gezielter Refactor)
- Alle ✓ → Effektor ist „done für Achse 1", Achse 2 (Lifecycle-Promotion) übernimmt

Konsumenten dokumentieren ihre Reife-Roadmap in eigenen Doku-Files; das Skelett-Repo führt keine Effektor-Tabelle, weil es keine konkreten Effektoren enthält (nur die drei Demos in `examples/`).

## Querschnittliche Reife-Themen

Schwellen die das Skelett selbst betreffen (Phase 6+ oder Konsumenten-Verantwortung):

- **Cross-Effector-Lesson-Bus**: Lessons aus Effektor A → Effektor B fließt heute manuell. EventBus (Phase 5.1) liefert die Mechanik, Konsumenten verdrahten Subscriber.
- **Lift-Tracking + Promotion**: Pattern-Promotion via `prompt_variant_promotion`-Plan ist Phase-6+-Erweiterung des LessonsAggregators.
- **Self-Improvement-Loop**: siehe [`06_SELF_IMPROVEMENT.md`](06_SELF_IMPROVEMENT.md), Konsumenten-Verantwortung.
- **OTel-Export**: Phase 4.3 liefert struktur-only Converter; echter HTTP-Push zu Langfuse/Jaeger ist Phase-7+.

Diese Lücken sind nicht Bug, sondern **Wachstumsschwellen**. Ein Konsumenten-Roadmap-Dokument ordnet sie nach Domänen-Bedarf.
