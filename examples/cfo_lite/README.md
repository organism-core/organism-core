# cfo_lite — Demo-Domain

Synthetische, **frei erfundene** Mini-Demo für ein CFO-Office. Treibt die volle Phase-1..5-Pipeline gegen 3 fake Reporting-Perioden (Quartals-Closes).

**Niemals** echte oder anonymisierte Finanzdaten. Alle Perioden und Close-Outputs sind frei erfunden.

## Lauf

```
python -m examples.cfo_lite
```

(aus dem repo-root). Verwendet ein temporäres Verzeichnis, druckt einen kompletten Pipeline-Walk auf stdout.

## Was die Demo zeigt

`kind=run_close_step`, 3 Entities (`2024-Q3`, `2024-Q4`, `2025-Q1`):

| Step | Stage | Was passiert |
|---|---|---|
| 1 | PROPOSED | Volle propose → approve → apply Sequenz für `2024-Q3` |
| 2 | CHECKED | 3 erfolgreiche Closes → Lifecycle-Promotion zu ROUTINE |
| 3 | AUTONOMOUS | Failing Effector → Revision-Loop, recordet Lessons, gibt mit `revision_pending=True` auf |
| 4 | (no run) | Manuelle HITL-Lesson „Q4-Closes benötigen Year-End-Reserve" mit `context_pattern={"quarter": 4}` |

## Trenn-Test

Identische Pipeline-Logik wie `architect_lite/` und `tax_lite/`. Nur Entity-Schema (Quartals-Frontmatter mit fiscal_year/quarter) und Effector-Returns sind domänen-spezifisch — die Orchestrator-Logik selbst ist wortgleich.

## API

```python
from pathlib import Path
from examples.cfo_lite import run_demo

summary = run_demo(Path("/tmp/my_run"))
```
