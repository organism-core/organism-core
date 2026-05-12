*[🇬🇧 English version](DEMOS.md)*

# DEMOS — Cross-Domain Genericity Validation

> Konzept-Skizze als Whitepaper-Vorbereitung für Phase 6.
> Stand: 2026-05-09, nach Phase 5.4.

## Motivation

Drei parallel implementierte Demo-Domains beweisen die zentrale Hypothese des Repos:

> **Dieselbe Pipeline-Codebasis funktioniert in drei verschiedenen Domänen ohne Anpassung der Orchestrator-/Engine-/Validator-/PlanGate-/Lifecycle-Logik.**

Wenn diese Hypothese fällt — z.B. weil ein Pattern Architekturbüro-spezifisch wäre — gehört das Pattern nicht ins Skelett. Die Demos sind die Lakmus-Probe.

## Die drei Demos

| Demo | Domain | Action-Kind | Effector | Entities |
|---|---|---|---|---|
| `architect_lite` | Architekturbüro | `extract_floor_plan` | `FloorPlanExtractor` | 3 Floor Plans (villa-alpha-basement, villa-alpha-ground, villa-beta-attic) |
| `tax_lite` | Steuerberatung | `validate_tax_return` | `TaxReturnValidator` | 3 Mandanten (client-042-2024, client-088-2024, gmbh-fischer-2024) |
| `cfo_lite` | CFO-Office | `run_close_step` | `QuarterlyCloseRunner` | 3 Reporting-Perioden (2024-Q3, 2024-Q4, 2025-Q1) |

Alle drei Domain-Daten sind **frei erfunden** — kein Anonymisierungspfad aus realen Daten.

## Pipeline-Walk (identisch in allen drei Demos)

| Step | Stage | Was passiert |
|---|---|---|
| 1 | PROPOSED | Volle propose → approve → apply Sequenz für eine Entity |
| 2 | CHECKED | 3 erfolgreiche Aktionen → Lifecycle-Promotion zu ROUTINE (`promote_after_n=3` für Demo-Sichtbarkeit) |
| 3 | AUTONOMOUS | Failing Effector → Revision-Loop (`autonomous_max_revision_attempts=2`), recordet Lessons, gibt mit `revision_pending=True` auf |
| 4 | (no run) | Manuelle HITL-Lesson via `aggregator.record_lesson()` |

## Trenn-Test-Resultat

Alle drei Demos produzieren **identische Pipeline-Counts**:

| Metrik | architect_lite | tax_lite | cfo_lite |
|---|---|---|---|
| Entities geseedet | 3 | 3 | 3 |
| Aktionen ausgeführt | 6 | 6 | 6 |
| Plans vorgeschlagen | 1 | 1 | 1 |
| Plans applied | 1 | 1 | 1 |
| Traces aufgezeichnet | 6 | 6 | 6 |
| Lessons aufgezeichnet | 3 | 3 | 3 |
| Events captured | 11 | 11 | 11 |
| Transitions beobachtet | 1 | 1 | 1 |
| Final stage | autonomous | autonomous | autonomous |

Event-Verteilung (identisch über alle drei):
- `plan_proposed`: 1
- `lifecycle_transition`: 1
- `trace_recorded`: 6
- `lesson_recorded`: 3

→ siehe `tests/examples/test_cross_demo.py` für die automatisierte Verifikation. Wenn dieser Test bricht, hat sich entweder die Pipeline domänen-spezifisch verhalten (Trenn-Test-Verstoß) oder eine Demo wurde inkonsistent geändert (sollte parallel-konsistent gehalten werden).

## Domain-Unterschiede

Was jedem Demo eigen ist (~100 Zeilen Code pro Demo):

```
examples/<demo>/
  entities.py     Entity-Schema mit Frontmatter-DoD-Kriterien
  effector.py     Effector-Klasse mit return_map (canned outputs)
  demo.py         Pipeline-Walk-Prosa (gleiche 4-Schritt-Struktur,
                  nur strings + KIND constant + decided_by-Name unterschiedlich)
  README.md       Domain-spezifische Anleitung
```

Was geteilt ist (`src/organism/`, ~3000 Zeilen):
- DoD-Engine + Validator (Phase 2)
- PlanGate (Phase 3.1)
- LifecycleManager (Phase 3.2)
- ActionOrchestrator + AUTONOMOUS-Revision (Phase 3.3 + 5.0)
- Event-Wiring (Phase 5.1)
- Provenance + TraceStore + LessonsAggregator + EventBus + ToolRegistry + OTel-Converter + Langfuse-Stub (Phase 4)
- Settings-Layer (Phase 3.0)

**Verhältnis**: ~10% Domain-Code, ~90% generischer Pipeline-Code. Eine vierte Domain (z.B. `legal_lite`, `medical_lite`) wäre wieder ~300 Zeilen.

## Demo als Vorlage für neue Konsumenten

Konsumenten, die eine eigene Domain integrieren wollen, kopieren eine bestehende Demo:

```bash
cp -r examples/tax_lite examples/my_domain
```

Dann anpassen:
1. `entities.py` — Entity-Schema mit eigenen Frontmatter-DoD-Kriterien
2. `effector.py` — `act()` mit echter Logik (statt return_map-Lookup); andere 4 Kontaktstellen oft pre_load=identity, define_done={}, upstream/gate trivial
3. `demo.py` — KIND constant, ggf. paar Print-Strings, decided_by-Name
4. `__init__.py`, `__main__.py`, `README.md` — Imports + Anleitung

Die Pipeline-Codebasis (`src/organism/`) wird **nicht angefasst**. Konsumenten erweitern via:
- Eigene Effectors (Phase 1.3 Protocol)
- Eigene DoD-Sources (Phase 2.1 Protocol) wenn nötig — Standard-6 reichen meist
- Eigene Settings-Klassen via `@register_settings(...)` falls deployment-spezifische Werte nötig

## Lauf

```bash
python -m examples.architect_lite
python -m examples.tax_lite
python -m examples.cfo_lite
```

(aus dem repo-root). Jede Demo verwendet ein temporäres Verzeichnis (`tempfile.TemporaryDirectory()`), druckt einen kompletten Pipeline-Walk auf stdout, räumt am Ende auf.

Library-Form für Tests / Konsumenten-Integration:

```python
from pathlib import Path
from examples.tax_lite import run_demo

summary = run_demo(Path("/tmp/my_run"))
print(summary.actions_executed)              # → 6
print(summary.event_types["lesson_recorded"]) # → 3
```

`run_demo(output_dir, print_fn=print)` nimmt optional `print_fn` für quiet-mode (Tests übergeben `lambda x: None`).

## Output-Beispiel (architect_lite, gekürzt)

```
==============================================================
  architect_lite -- DoD-Pipeline-Walk
  3 synthetische Entities, kind=extract_floor_plan
==============================================================

[SETUP]
  Stores in /tmp/architect_lite_xyz
  Engine: 6 Sources (default), Threshold=0.5
  Lifecycle: initial=proposed, promote_after_n=3

[SEEDING]
  villa-alpha-basement (residential/basement, 2 Kriterien)
  villa-alpha-ground (residential/ground, 2 Kriterien)
  villa-beta-attic (residential/attic, 1 Kriterien)

[STEP 1] Stage PROPOSED -- propose -> approve -> apply
  execute() -> status=proposed, plan=35373c52...
  plan_gate.approve(...)
  apply_approved_plan() -> status=applied, score=1.00

[STEP 2] Stage CHECKED -- set_stage + 3 actions -> promotion
  villa-alpha-basement: status=applied, score=1.00
  villa-alpha-ground: status=applied, score=1.00
  villa-beta-attic: status=applied, score=1.00 -> TRANSITION checked -> routine
  Lifecycle nach Step 2: stage=routine

[STEP 3] Stage AUTONOMOUS -- failing effector -> revision-loop
  execute() -> status=applied, score=0.00, revision_attempts=2, revision_pending=True
  -> 2 Revision-Lessons aufgezeichnet

[STEP 4] Manuelle HITL-Lesson
  aggregator.record_lesson(...)

[SUMMARY]
  Aktionen ausgefuehrt:   6
  Plans vorgeschlagen:    1
  Traces aufgezeichnet:   6
  Lessons aufgezeichnet:  3
  Events captured:        11
  Finale Stage:           autonomous

  Event-Typen:
    lesson_recorded: 3
    lifecycle_transition: 1
    plan_proposed: 1
    trace_recorded: 6
```

`tax_lite` und `cfo_lite` produzieren strukturell identischen Output mit Domain-spezifischen Werten.

## Status & Offene Fragen

### Phase 5 Liefer-Stand (Stand 2026-05-09)

- 5.0 AUTONOMOUS-Revision-Loop (Lesson-Feedback in Orchestrator)
- 5.1 Event-Wiring (Orchestrator + LessonsAggregator publishen)
- 5.2 architect_lite demo
- 5.3 tax_lite demo
- 5.4 cfo_lite demo
- 5.5 docs/DEMOS.md + Cross-Demo-Verifikations-Test
- ~500 Tests grün

### Bewusst nicht in Phase 5

- **Plan-Gate-UI**: kein Web-Cockpit. Demos simulieren approve direkt via API.
- **Auto-ToolRegistry-Registrierung**: Effectors registrieren manuell (oder gar nicht, wie in Demos).
- **Echter HTTP-Push zu Langfuse**: Adapter ist Stub, Demos verwenden ihn nicht.
- **Karpathy-Loop / Self-Improvement-Loop**: Phase 6+ Themen oder gestrichen.
- **Multi-Step Demos**: nur 4 Schritte je Demo. Komplexere Workflows wären Erweiterung pro Konsument.

### Offene Fragen für Phase 6 (Whitepaper-Konsolidierung)

- **`docs/ARCHITEKTUR/` entkernen**: heute domänen-gefärbt aus dem Bestand. Phase 6 macht generisch.
- **Whitepaper für Public-Release**: STAR.md + LIFECYCLE.md + OBSERVABILITY.md + DEMOS.md zusammenführen oder als modulare Whitepapers publishen?
- **Demo als executable spec**: könnten die Demos in Phase 6 zu CI-Smoketests werden? (Heute schon via pytest-tests, aber CI-Setup fehlt.)
- **CLI-UX**: heute simple print. Phase 6+ vielleicht `rich`-Output für Lesbarkeit (terminal colors, tables)?
- **Demo-Sharing**: heute ist Setup-Code dupliziert über 3 Demos (~80 Zeilen pro Demo). Ein `examples/_common/`-Helper wäre DRY, aber Konsumenten würden dann erst kopieren+anpassen müssen. Bewusste Wahl in Phase 5: Duplikation für Vorlage-Tauglichkeit. Phase 6 könnte das überdenken.
- **Echte Effector-Logik**: heute deterministischer return_map-Lookup. Konsumenten implementieren echte Effectors mit Vision-LLM-Calls / Tax-Logic / Close-Berechnungen.
- **Cross-Demo-Tests in CI**: heute lokal grün. Phase 6+ pipeline.
