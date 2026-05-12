## Was ändert sich?

<!-- Knappe Beschreibung der Änderung. Bei mehreren Punkten: Liste. -->

## Trenn-Test

> **„Würde dieselbe Logik in einer Steuerberatung Sinn ergeben?"**

- [ ] Code-Änderung im `src/organism/`: Trenn-Test bestanden (kein domänen-spezifisches Vokabular)
- [ ] Tests grün (`pytest tests/`)
- [ ] Cross-Domain-Verifikation grün (`pytest tests/examples/test_cross_demo.py`)
- [ ] Falls neue Settings: in `config/`-YAML mit Kommentar hinzugefügt
- [ ] Falls neuer Effektor in `examples/`: alle 3 Demos zeigen identische Pipeline-Counts

## Welche Phase betrifft das?

<!-- 1 (Memory/Effector) / 2 (DoD) / 3 (Plan-Gate/Lifecycle) / 4 (Observability)
     / 5 (Demos+Revision+Events) / 6 (Doku/Konsolidierung) -->

## Bezug zu existierenden Docs

<!-- Falls Pattern-Erweiterung: welches docs/-Dokument wird aktualisiert?
     STAR.md / LIFECYCLE.md / OBSERVABILITY.md / DEMOS.md / M5_WHITEPAPER.md /
     ARCHITEKTUR/<chapter>.md -->

## Breaking Changes

<!-- Falls API ändert: welche Konsumenten-Signaturen brechen? Migration-Hinweis. -->
