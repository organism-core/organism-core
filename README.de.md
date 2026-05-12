*[🇬🇧 English version](README.md)*

# organism-core

**Quality-gated multi-tool AI orchestration.**

Referenz-Implementierung, die vor jeder Aktion eine Definition-of-Done recherchiert, das Ergebnis gegen die abgeleiteten Kriterien validiert und Lifecycle-Stages aus dem Score-Verlauf treibt.

**Status**: Phase 0-7 + Cockpit-UI-Layer + Querier-Lineage

## Was ist das?

Ein opinionated Pattern-Set für Systeme, in denen mehrere KI-Tools parallel arbeiten und ihre Ergebnisse in einen zentralen Wahrheits-Speicher konsolidieren. Das Skelett liefert die generischen Bausteine (DoD-Engine, Lifecycle-State-Machine, Plan-Gate, Lessons-Aggregator, Trace-Store, EventBus, Cockpit). Konsumenten implementieren konkrete Effektoren und Querier für ihre Domäne.

## Was macht das anders

Drei Primitive, die in den etablierten Multi-Agent-Frameworks (LangGraph, CrewAI, AutoGen, Microsoft Agent Framework, AgentScope) **nicht** als First-Class-Konzepte vorkommen:

1. **DoD-Recherche als Pre-Action-Research.** Vor jeder Aktion mit Außenwirkung recherchiert das System die Definition of Done aus sechs priorisierten Quellen (Entity-Profile, Lessons, verwandte Entities, Vector-Search, Domain-Patterns, User-Klärung). Validiert das Ergebnis gegen die abgeleiteten Kriterien nach `act()`. Detail im [`docs/M5_WHITEPAPER.de.md`](docs/M5_WHITEPAPER.de.md).

2. **Cross-Domain-Genericity als executable spec.** Ein CI-Test stellt sicher, dass drei Demo-Domains (z.B. Architektur, Steuer, CFO) identische Pipeline-Counts produzieren. Wenn ein Beitrag das Framework versehentlich domänen-spezifisch macht, bricht der Test. Kein anderes Framework publiziert solch einen automatisierten Genericity-Wächter.

3. **Score-getriebene Lifecycle-Stages.** Effektoren steigen `(a)→(b)→(c)→(d)→(e)` auf basierend auf demonstrierter Qualität (avg Score über rolling window) und steigen bei Drift ab. Stages sind keine Abzeichen — sie werden verdient und automatisch entzogen.

Das ist **komplementär** zu self-evolving Agents (z.B. Hermes Agent) und zu LLM-basierten Reasoning-Agents — nicht in Konkurrenz dazu. organism-core liefert die Validierungs-, Lifecycle- und Observability-Schicht; der Reasoning-Agent läuft darauf.

Read-only Tools haben eine eigene schmale Lineage (`organism.query`), die DoD/Plan-Gate/Lifecycle-Zeremonie überspringt — Details im [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Quick Start

```bash
git clone git@github.com:organism-core/organism-core.git
cd organism-core
pip install -e ".[dev]"

# Eine der 3 Demo-Domains laufen lassen (Action-Side, Pipeline-Walk):
python -m examples.architect_lite    # Architekturbüro
python -m examples.tax_lite          # Steuerberatung
python -m examples.cfo_lite          # CFO-Office

# Oder die DoD-Recherche durch alle 6 Quellen sehen:
python -m examples.full_recherche

# Oder das headless UI-Wesen (Cockpit) in Aktion:
python -m examples.cockpit_demo

# Tests laufen:
pytest tests/
```

Die drei Domain-Demos drucken einen kompletten Pipeline-Walk (Setup → Seeding → 4 Schritte: PROPOSED-Flow, CHECKED-Promotion, AUTONOMOUS-Revision, HITL-Lesson) auf stdout. Alle drei produzieren **identische Pipeline-Counts** — Cross-Domain-Verifikation als executable spec.

`full_recherche` ist ein vierter Demo-Modus mit anderem Fokus: er zeigt die **6-Source-Hierarchie** der DoD-Recherche-Engine (M5) im Vollausbau, mit synthetischen Implementierungen der drei Stub-Quellen (RelatedEntities / VectorSearch / DomainPattern) als Vorlage für Konsumenten.

`cockpit_demo` zeigt das headless UI-Wesen — der Cockpit hovert über Orchestrator und Stores und liefert getypte Render-Schemas (DoDView / PlanApprovalView / DriftView / QueryTraceView) an beliebige UI-Frameworks.

## Lesepfad

| Wer du bist | Lies |
|---|---|
| Erstmal Überblick | [`docs/M5_WHITEPAPER.de.md`](docs/M5_WHITEPAPER.de.md) (single-document) |
| DoD-Engine im Detail | [`docs/STAR.de.md`](docs/STAR.de.md) |
| Plan-Gate + Lifecycle | [`docs/LIFECYCLE.de.md`](docs/LIFECYCLE.de.md) |
| Observability + Lessons | [`docs/OBSERVABILITY.de.md`](docs/OBSERVABILITY.de.md) |
| Demos + Genericity-Beweis | [`docs/DEMOS.de.md`](docs/DEMOS.de.md) |
| Architektur-Konzepte (deutsch) | [`docs/ARCHITEKTUR/`](docs/ARCHITEKTUR/) (11 Kapitel) |
| Governance + Trenn-Vertrag | [`docs/STRATEGIE-EXTRACT.de.md`](docs/STRATEGIE-EXTRACT.de.md) |
| 2-Sprachen-Konvention | [`docs/TRANSLATION_GUIDE.md`](docs/TRANSLATION_GUIDE.md) |

Index aller Docs: [`docs/README.de.md`](docs/README.de.md).

## Module

| Pfad | Aufgabe | Phase |
|---|---|---|
| `src/organism/memory/` | Entity-Memory (YAML+MD pro Entity), schema-frei | ✅ 1 |
| `src/organism/adapter/` | 5-Kontakt-Effektor-Vertrag (Protocol + BaseEffector + ReadEffector) | ✅ 1 |
| `src/organism/query/` | 2-Kontakt-Querier-Vertrag + QueryRunner (read-only Pfad) | ✅ Q |
| `src/organism/dod/` | DoD-Recherche-Engine (Star-Pattern, M5) — Kernstück | ✅ 2 |
| `src/organism/settings/` | YAML-roundtripable Settings + Registry für Admin-UI | ✅ 3 |
| `src/organism/plan_gate/` | Approve/Reject-Service mit File-backed Plan-Persistierung | ✅ 3 |
| `src/organism/lifecycle/` | State-Machine `(a)→(e)` mit avg-Score-getriebenen Transitions | ✅ 3 |
| `src/organism/orchestrator/` | ActionOrchestrator: Stage-Routing + AUTONOMOUS-Revision-Loop | ✅ 3+5 |
| `src/organism/provenance/` | Provenance-Container (author/source/confidence/...) | ✅ 4 |
| `src/organism/observability/` | TraceStore + QueryTraceStore, EventBus, ToolRegistry, OTel, Langfuse-Stub | ✅ 4 |
| `src/organism/lessons/` | LessonsAggregator + LessonsSource | ✅ 4 |
| `src/organism/ui/` | Cockpit + Render-Schemas + UIEventStream (headless UI-Layer) | ✅ UI |

## Demo-Domains

`examples/<demo>/` — parallele Mini-Demos als Generizitäts-Disziplin. Was nicht in allen drei läuft, ist zu domänen-spezifisch:

- `examples/architect_lite/` — Architekturbüro-Lite (Floor-Plan-Extraktion + Lookup-Querier)
- `examples/tax_lite/` — Steuerberatungs-Lite (Steuererklärungs-Validierung + Querier)
- `examples/cfo_lite/` — CFO-Lite (Quartals-Closes + Cost-Center-Querier)
- `examples/full_recherche/` — Zeigt die 6-Source-DoD-Hierarchie im Vollausbau
- `examples/cockpit_demo/` — Zeigt das Cockpit-Wesen mit allen Render-Schemas

Jede Domain-Demo ist self-contained (~300 Zeilen) — als Vorlage zum Kopieren für eigene Domänen geeignet.

## Phasenstand

| Phase | Status | Inhalt |
|---|---|---|
| 0 | ✅ | Repo-Init, leere Modul-Struktur |
| 1 | ✅ | Memory + Effector-Vertrag (BaseEffector + ReadEffector) |
| 2 | ✅ | DoD-Engine + 6 Sources + Validator |
| 3 | ✅ | Settings + PlanGate + Lifecycle + Orchestrator |
| 4 | ✅ | Provenance + Trace + Lessons + EventBus + OTel + Langfuse |
| 5 | ✅ | AUTONOMOUS-Revision + Event-Wiring + 3 Demos + Cross-Demo-Test |
| 6 | ✅ | Doku-Konsolidierung + M5-Whitepaper + LICENSE + CI |
| 7 | ✅ | M5-Patch-Code: evaluator-Switch + Lesson-Loop + Revisions-Strategien + Operative Settings |
| UI | ✅ | Cockpit-Wesen + Render-Schemas + UIEventStream + CockpitBuilder |
| Q | ✅ | Querier-Lineage (read-only): Protocol + Runner + QueryTrace + Cockpit-Integration |

Detail-Status in [`MEMORY.md`](MEMORY.md).

## Test

```bash
pytest tests/
```

712 Tests grün. Zwei Trenn-Test-Wächter:
- `tests/examples/test_cross_demo.py` — Action-Side: alle 3 Domain-Demos produzieren identische Pipeline-Counts
- `tests/examples/test_cross_demo_queries.py` — Query-Side: alle 3 Domain-Querier produzieren identische Trace-Counts

`tests/examples/test_m5_features.py` ist der M5-Patch-Code-Wächter für die Per-Domain-Features (evaluator / Revisions-Strategien / operative Settings).

## License

Apache License 2.0 — siehe [`LICENSE`](LICENSE).

Contributions werden unter dem Contributor License Agreement des
Projekts angenommen (siehe [`CLA.md`](CLA.md)). Du behältst das
Copyright an deinem Beitrag; du gewährst dem Projekt die Rechte, die
es zum Veröffentlichen und Weiterentwickeln braucht.

## Repository

https://github.com/organism-core/organism-core

---

*Mensch ist Kurator, KI ist Vorschlag.*
