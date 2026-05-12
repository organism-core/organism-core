# architect_lite — Demo-Domain

Synthetische, **frei erfundene** Mini-Demo für ein Architekturbüro-Szenario. Treibt die volle Phase-1..5-Pipeline gegen 3 fake Floor-Plan-Entities.

**Niemals** echte oder anonymisierte Daten — Strukturmuster sickern durch Anonymisierung durch. Alle Entitäten und Floor-Plan-Outputs sind frei erfunden.

## Lauf

```
python -m examples.architect_lite
```

(aus dem repo-root). Verwendet ein temporäres Verzeichnis, druckt einen kompletten Pipeline-Walk auf stdout.

## Was die Demo zeigt

`kind=extract_floor_plan`, 3 Entities (`villa-alpha-basement`, `villa-alpha-ground`, `villa-beta-attic`):

| Step | Stage | Was passiert |
|---|---|---|
| 1 | PROPOSED | Volle propose → approve → apply Sequenz für `villa-alpha-basement` |
| 2 | CHECKED | 3 erfolgreiche Aktionen → Lifecycle-Promotion zu ROUTINE |
| 3 | AUTONOMOUS | Failing Effector → Revision-Loop läuft `autonomous_max_revision_attempts=2` mal, recordet Lessons, gibt schließlich auf mit `revision_pending=True` |
| 4 | (no run) | Manuelle HITL-Lesson via `aggregator.record_lesson(...)` |

Output umfasst: aufgezeichnete Traces, Lessons, Events (`plan_proposed`, `lifecycle_transition`, `trace_recorded`, `lesson_recorded`), finalen Stage.

## API

```python
from pathlib import Path
from examples.architect_lite import run_demo

summary = run_demo(Path("/tmp/my_run"))
print(summary.actions_executed, summary.events_captured)
```

`run_demo` nimmt optional `print_fn` für quiet mode (z.B. tests).

## Trenn-Test

Identische Pipeline-Logik wie `tax_lite/` und `cfo_lite/`. Nur Entity-Schema und Effector-Returns sind domänen-spezifisch — die Orchestrator-Logik selbst ist generisch.
