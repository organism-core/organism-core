*[🇬🇧 English version](README.md)*

# Docs Index

Vollständige Dokumentation des organism-core-Skeletts. Beginne mit [`M5_WHITEPAPER.de.md`](M5_WHITEPAPER.de.md) für einen single-document-Überblick.

## Whitepaper-Drafts (public-ready)

Konsolidierte und thematische Whitepaper-Skizzen. Public-tauglich, keine internen Verweise.

| Doc | Inhalt | Länge |
|---|---|---|
| [`M5_WHITEPAPER.de.md`](M5_WHITEPAPER.de.md) | **Single-document Whitepaper** zum Teilen — M5-Pattern, Architektur-Kontext, Cross-Domain-Verifikation, References | 370 Zeilen |
| [`STAR.de.md`](STAR.de.md) | DoD-Engine deep-dive — 6-Quellen-Hierarchie, Comparator-Semantik, Cross-Domain-Beispiele | 281 Zeilen |
| [`LIFECYCLE.de.md`](LIFECYCLE.de.md) | Plan-Gate + Lifecycle-State-Machine — Stages `(a)→(e)`, Stage-Transitions, ActionOrchestrator | 270 Zeilen |
| [`OBSERVABILITY.de.md`](OBSERVABILITY.de.md) | Trace + Lessons + EventBus + OTel — vollständige Beobachtungs-Schicht | 330 Zeilen |
| [`DEMOS.de.md`](DEMOS.de.md) | Cross-Domain-Validierung — 3 Demo-Domains mit identischen Pipeline-Counts | 290 Zeilen |
| [`PRODUCTION_DEFAULT.md`](PRODUCTION_DEFAULT.md) | Adoption-Lesson — explizites Plan/HITL/Dispatch ist Produktions-Default; der autonome Reflexbogen bleibt Forschungs-Track (englisch) | ~100 Zeilen |
| [`MCP_DESIGN.md`](MCP_DESIGN.md) | MCP-Audit + stateless-by-design-Constraints für künftige Adapter, ausgerichtet am RC 2026-07-28 (englisch) | ~80 Zeilen |

## Architektur-Konzepte

Strukturelle Doku in 11 Kapiteln. Jedes ist generisch geschrieben (Phase 6 entkernt), Verweise auf die Whitepaper-Drafts oben für Implementations-Details.

| Kapitel | Inhalt |
|---|---|
| [`ARCHITEKTUR/00_LEITBILD.md`](ARCHITEKTUR/00_LEITBILD.md) | 3 Grundprinzipien (file-based truth, Mensch-Kurator, semi-autonome Effektoren) |
| [`ARCHITEKTUR/01_ANATOMIE.md`](ARCHITEKTUR/01_ANATOMIE.md) | Komponenten-Übersicht — Effektoren + zentrales System |
| [`ARCHITEKTUR/02_NERVENSYSTEM.md`](ARCHITEKTUR/02_NERVENSYSTEM.md) | 3 Koordinations-Schichten (Reflex / Insight / Plan / Lerntakt) |
| [`ARCHITEKTUR/03_GEDAECHTNIS.md`](ARCHITEKTUR/03_GEDAECHTNIS.md) | 4 Memory-Ebenen (External / EntityStore / Vector / RAM) |
| [`ARCHITEKTUR/04_LERNEN.md`](ARCHITEKTUR/04_LERNEN.md) | 3 Lern-Schleifen (HITL / Few-Shot / Self-Improvement) |
| [`ARCHITEKTUR/05_REFLEXBOGEN.md`](ARCHITEKTUR/05_REFLEXBOGEN.md) | P1-P10 verbindliche Patterns für alle Effektoren |
| [`ARCHITEKTUR/06_SELF_IMPROVEMENT.md`](ARCHITEKTUR/06_SELF_IMPROVEMENT.md) | Self-Improvement-Loop + Reinforcement-Tracking-Konzept |
| [`ARCHITEKTUR/07_REIFEGRAD.md`](ARCHITEKTUR/07_REIFEGRAD.md) | 2-Achsen-Bewertungs-Framework für Effektor-Reife |
| [`ARCHITEKTUR/08_GOLD_PATTERNS.md`](ARCHITEKTUR/08_GOLD_PATTERNS.md) | Meta-Patterns M1-M5 quer durchs System |
| [`ARCHITEKTUR/09_FRAMEWORK.md`](ARCHITEKTUR/09_FRAMEWORK.md) | Universelles Framework — 5 Bauteile + Lifecycle-Stages |
| [`ARCHITEKTUR/10_LANDSCHAFT.md`](ARCHITEKTUR/10_LANDSCHAFT.md) | Skelett im Ökosystem — USPs, Inspirations-Quellen, References |

## Governance

| Doc | Inhalt |
|---|---|
| [`STRATEGIE-EXTRACT.de.md`](STRATEGIE-EXTRACT.de.md) | Trenn-Vertrag: was ins Skelett gehört, was nicht; Generizitäts-Disziplin |

## Lesepfade nach Anwendungsfall

### „Ich will nur verstehen worum es geht" (15 Min)

- [`M5_WHITEPAPER.de.md`](M5_WHITEPAPER.de.md) Abstract + Sections 1-3

### „Ich will den DoD-Ansatz verstehen" (30 Min)

- [`M5_WHITEPAPER.de.md`](M5_WHITEPAPER.de.md) komplett
- [`STAR.de.md`](STAR.de.md) für Engine-Details

### „Ich will eine eigene Domain anschließen" (1-2 Stunden)

- [`M5_WHITEPAPER.de.md`](M5_WHITEPAPER.de.md) — Pattern-Überblick
- [`DEMOS.de.md`](DEMOS.de.md) — Vorlage-Anleitung
- [`examples/tax_lite/`](../examples/tax_lite/) als konkretes Vorbild
- [`ARCHITEKTUR/05_REFLEXBOGEN.md`](ARCHITEKTUR/05_REFLEXBOGEN.md) — P1-P10 als Sanity-Check

### „Ich evaluiere als Architekt eine Adoption" (2-3 Stunden)

- [`M5_WHITEPAPER.de.md`](M5_WHITEPAPER.de.md)
- [`ARCHITEKTUR/`](ARCHITEKTUR/) alle 11 Kapitel
- [`OBSERVABILITY.de.md`](OBSERVABILITY.de.md) für OTel-Integration
- [`STRATEGIE-EXTRACT.de.md`](STRATEGIE-EXTRACT.de.md) für Governance

### „Ich will die Implementation lesen"

- Code in [`../src/organism/`](../src/organism/) modul-weise
- Tests in [`../tests/`](../tests/) als Spec

## Verweise

- [`../README.md`](../README.md) — Repo-Hauptseite mit Quick Start
- [`../CONTRIBUTING.md`](../CONTRIBUTING.md) — Contribution- und Trenn-Test-Leitfaden
