# 05 — Reflexbogen (Verbindliche Patterns)

> Welche Verhaltensregeln müssen ALLE Effektoren einhalten?

Diese Patterns sind verbindlich. Wer sie verletzt, baut Bugs. Sie sind nach Wichtigkeit sortiert.

## P1 — Steckbrief-zuerst (Pre-Lookup)

**Regel**: Bevor ein Effektor eine inhaltliche Aktion startet, muss er den Steckbrief der betroffenen Entity gelesen haben.

**Warum**: ein Klinik-Plan im Maßstab 1:50 hat andere Wand-Stärken, andere Tür-Größen, andere Raumzahlen als ein Wohnbau. Wenn der Effektor vor der Bildanalyse weiß „wohnbau, 1:50, etwa 30 Zimmer", kann er sein Erwartungs-Modell entsprechend kalibrieren — Sanity-Filter greifen früher, LLM-Calls sind gezielter.

**Mechanik**:

```python
from organism.memory import EntityStore

store = EntityStore(root_path)
entity = store.read(entity_id)
# entity.frontmatter["type"] -> domain-spezifische Kategorie
# entity.frontmatter["dod"]["criteria"] -> bekannte Erwartungen
```

Realisiert über `Effector.pre_load(context)` (siehe [`08_GOLD_PATTERNS.md`](08_GOLD_PATTERNS.md), M1).

Wenn keine Entity gewählt: Effektor fragt User (siehe P2), schaut nicht halb-blind weiter. Eine „ich habe keinen Steckbrief, das ist OK weil ..."-Antwort ist falsch.

## P2 — Frag den User bevor du rätst

**Regel**: Wenn ein Effektor eine kritische Annahme treffen muss, die er nicht aus Steckbrief/Cross-Reference ableiten kann, fragt er den User **vor** der Aktion. Maximal 2-3 Fragen, knapp formuliert.

**Warum**: drei gezielte User-Fragen am Anfang ersparen 30 Korrekturen am Ende. Plus: User-Antwort wird Lesson, nicht nur Session-State.

**Mechanik**:

- Im Skelett: DoD-Engine recherchiert via `engine.derive(...)` durch 6 Quellen. Wenn nicht alle satisfied: `UserClarificationSource` (Phase 2.1) liefert `clarification_needed`-Liste. Orchestrator returnt `ActionStatus.NEEDS_CLARIFICATION` — Aktion läuft nicht.
- UI-Ebene (Phase 7+): Caller kann die Klärungen als Pre-Pass-Card mit Eingabefeldern dem User zeigen.

Anti-Muster: Effektor nimmt Default an, schreibt Result, User merkt Fehler erst beim Sichten. Das ist eine **Versäumnis-Falle**, nicht eine Komplexitäts-Falle.

## P3 — Provenance-Pflicht

**Regel**: Jeder KI-erzeugte Eintrag in den Wahrheits-Speicher hat ein `_provenance: {author, source, confidence, validated_by_user, timestamp}`-Block.

**Mechanik**:

```python
from organism.provenance import Provenance

prov = Provenance.now(
    author="my_effector",
    source="Vision-Call zu PDF X vom 2026-04-12",
    confidence=0.85,
)
# ... hänge prov an den Output ...
```

Detail: [`docs/OBSERVABILITY.de.md`](../OBSERVABILITY.de.md).

Ohne Provenance ist ein Eintrag nicht zurückführbar. Bei Konflikten zwischen zwei Aussagen entscheidet `validated_by_user` (true gewinnt über false), dann `confidence`.

## P4 — Keine Schreibaktion ohne Plan-Gate (außer Reflex-Schicht)

**Regel**: Wer in den Wahrheits-Speicher schreibt mit nicht-trivialer Wirkung, geht durchs Plan-Gate (`plan_gate.propose` → User-Approve → `apply`).

**Was „nicht-trivial" bedeutet**: jede Aktion, die ein Mensch nicht ohne Sichtkontrolle revertieren würde. Gegenbeispiele die OK sind:

- Audit-Log-Eintrag in `_aenderungen.yaml` (Append-Only, harmlos)
- Cache-Datei in `.cache/`
- Index-Update (Metadaten zu schon vorhandenen Dateien)

Was Plan-Gate braucht:

- Steckbrief-Update mit neuen Fakten
- Strukturelle Schreibvorgänge (Geometrie, Konfiguration)
- Conflict-Resolution-Apply
- Code-Patches (siehe [`06_SELF_IMPROVEMENT.md`](06_SELF_IMPROVEMENT.md))

Realisiert über `organism.plan_gate.PlanGate` (Phase 3.1) und `organism.lifecycle.LifecycleManager` (Phase 3.2). Detail: [`docs/LIFECYCLE.de.md`](../LIFECYCLE.de.md).

## P5 — Externe Quellen sind read-only

**Regel**: Code im Skelett darf NICHT in die externe Quelle (Mounted Filesystem, DMS, externes API der Domäne) schreiben. Punkt.

Test: grep nach Schreib-Operationen auf externe-Quelle-Pfade — wenn gefunden ist es ein Bug.

Detail: [`03_GEDAECHTNIS.md`](03_GEDAECHTNIS.md).

## P6 — Menschenlesbar oder gar nicht

**Regel**: Strukturierte Daten im Wahrheits-Speicher sind YAML oder Markdown. Kein JSON (Kommentare nicht erlaubt), kein Pickle, kein proprietäres Binärformat.

Ausnahme: Vector-Store intern (parquet-/binär-Files je nach Backend) — aber das ist Suchindex, nicht Wahrheit.

## P7 — Capabilities expose, keine Magic-Strings

**Regel**: Wenn ein Effektor eine Operation anbietet, sollte sie über die `ToolRegistry` discoverbar sein. Andere Komponenten rufen sie über das Schema auf, nicht via internem Funktions-Import.

**Warum**: Effektoren sollen austauschbar sein. Wer importiert-koppelt, kann nicht mehr ohne Verkehrschaos refactoren.

Realisiert über `organism.observability.ToolRegistry` (Phase 4.3). Auto-Registrierung beim Effektor-Konstruktor ist Phase-7+-Verantwortung der Konsumenten.

## P8 — Lesson-Schreibe-Pflicht

**Regel**: Wo ein User korrigiert, schreibt der Effektor eine Lesson. Nicht nur „session.edits applied", sondern persistent für Lesson-Aggregator-Pickup.

```python
from organism.lessons import LessonsAggregator

aggregator.record_lesson(
    kind="my_action_kind",
    observation="User korrigierte X auf Y",
    criteria_hint=[Criterion(name="...", expected="...")],
    confidence_delta=0.1,
    context_pattern={"feature_a": "value"},
)
```

Anti-Muster: User klickt „delete element", die Session wird upgedated, aber kein Eintrag im LessonsStore. Dann lernt das System nie aus dieser Korrektur.

Detail: [`04_LERNEN.md`](04_LERNEN.md), [`docs/OBSERVABILITY.de.md`](../OBSERVABILITY.de.md).

## P9 — Health- und Capabilities-Endpoint

**Regel** (für Effektoren, die als Service exponiert sind, Phase 7+): `/api/<effector>/health` (alive?) und `/api/<effector>/capabilities` (was kann ich?).

Health darf nie werfen, auch wenn der Effektor kaputt ist (Status mit `alive: false, error: ...`). Damit das System Effektoren auch bei Fehlern identifizieren kann.

Im Skelett heute nicht relevant — Skelett liefert die Datenklassen (`RegisteredTool`), Service-Exposition ist Konsumenten-Aufgabe.

## P10 — Reflexivität vor Ambition

**Regel**: Bevor ein Effektor sich selbst verbessert, muss er nachprüfbar sein. Kein Self-Improvement-Worker, der Code-Änderungen vorschlägt, ohne dass der entsprechende Trace-Pfad fest ist.

Realisiert: TraceStore (Phase 4.1) + Plan-Gate (Phase 3.1) als Doppel-Sicherung. AUTONOMOUS-Revision-Loop (Phase 5.0) als gated Erweiterung — Lessons werden bei Validation-Verfehlung aufgezeichnet, retry mit max-attempts-Cap, kein wilder Retry-Sturm.

## Sanity-Check für neue Effektoren

Wenn ein neuer Effektor dazukommt, gehe diese Liste durch:

- [ ] Liest er Entity-Steckbrief vor Aktion? (P1, via `pre_load`)
- [ ] Frägt er bei Unklarheit User? (P2, via DoD `clarification_needed`)
- [ ] Hat jeder schreibbare Output Provenance? (P3)
- [ ] Schreibwege durch Plan-Gate? (P4, ab Lifecycle-Stage `(b) PROPOSED`)
- [ ] Keine Schreibe in externe Quelle? (P5)
- [ ] YAML/Markdown statt JSON/Pickle? (P6)
- [ ] Capabilities-Schema da? (P7, via ToolRegistry)
- [ ] Lesson-Hook auf User-Korrektur? (P8)
- [ ] Health-Endpoint? (P9, falls Service-exponiert)
- [ ] TraceStore + Plan-Gate doppelt gesichert wenn selbstverbessernd? (P10)

Acht Häkchen sind Mindestanspruch. Neun-Zehn sind die Norm.

Demos in `examples/<demo>/effector.py` zeigen ein minimales Effektor-Skelett, das die meisten Patterns erfüllt — als Vorlage für eigene Implementierungen.
