# tax_lite — Demo-Domain

Synthetische, **frei erfundene** Mini-Demo für eine Steuerberatung. Treibt die volle Phase-1..5-Pipeline gegen 3 fake Mandanten-Steuererklärungen.

**Niemals** echte oder anonymisierte Daten. Alle Mandanten und Validierungs-Outputs sind frei erfunden.

## Lauf

```
python -m examples.tax_lite
```

(aus dem repo-root). Verwendet ein temporäres Verzeichnis, druckt einen kompletten Pipeline-Walk auf stdout.

## Was die Demo zeigt

`kind=validate_tax_return`, 3 Entities (`client-042-2024`, `client-088-2024`, `gmbh-fischer-2024`):

| Step | Stage | Was passiert |
|---|---|---|
| 1 | PROPOSED | Volle propose → approve → apply Sequenz für `client-042-2024` |
| 2 | CHECKED | 3 erfolgreiche Validierungen → Lifecycle-Promotion zu ROUTINE |
| 3 | AUTONOMOUS | Failing Effector → Revision-Loop, recordet Lessons, gibt mit `revision_pending=True` auf |
| 4 | (no run) | Manuelle HITL-Lesson „GmbH-Mandanten benötigen ust_id-Check" |

## Trenn-Test

Identische Pipeline-Logik wie `architect_lite/` und `cfo_lite/`. Nur Entity-Schema (Mandanten-Typ, fiscal_year statt floor) und Effector-Returns sind domänen-spezifisch — die Orchestrator-Logik selbst ist wortgleich.

## API

```python
from pathlib import Path
from examples.tax_lite import run_demo

summary = run_demo(Path("/tmp/my_run"))
```
