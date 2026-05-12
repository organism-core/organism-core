# 10 — Landschaft

> Wo steht das Skelett im breiteren Ökosystem? Was sind die USPs, was die Inspirations-Quellen?

## Mainstream-Alignment

Das Skelett bewegt sich im Strom, nicht exotisch. Drei zentrale Pattern werden **branchenweit konvergent** entwickelt:

- **File-First-Memory mit YAML+Markdown** — Anthropic Agent Skills (Dezember 2025), Letta-Studie 2026 („Filesystem all you need", 74% vs 68.5% LoCoMo), `_entity_profile.md`-Pattern dieses Skeletts. Markdown-File-Memory schlägt Vector-Graph-Memory empirisch.
- **Provenance-Pflicht** — OpenTelemetry GenAI Semantic Conventions, OTel-konforme `Provenance`-Container (Phase 4.0). Industry-Standard für Audit-Trails.
- **Plan-Gate / Human-in-the-Loop für Schreibaktionen** — LangGraph `interrupt_on`, PydanticAI `requires_approval`, gotoHuman MCP-Adapter, HumanLayer ACP. Konvergent bei „Mensch ist Kurator, KI ist Vorschlag".
- **Lifecycle-Stufen für Aktions-Reife** — Knight Institute (arXiv 2506.12469) „Levels of Autonomy for AI Agents" mit 5 Stufen. ~70% Match zu (a)→(e) im Skelett, aber per User-Rolle statt per Aktion (Skelett ist granularer).

## USPs des Skeletts

Wo das Skelett von verbreiteten OSS-Lösungen abweicht — bewusste Designentscheidungen:

### USP 1 — File-First-Memory mit Steckbrief-Konvention

Letta/Mem0/Zep sind alle DB-zentriert. Cognee + Anthropic Skills validieren den Skelett-Pfad, aber das Skelett geht weiter mit der **Steckbrief-Konvention** (`_entity_profile.md` mit YAML-Frontmatter inkl. `dod.criteria` als Pflichtfeld für DoD-Engine-Integration).

### USP 2 — DoD-Engine als 6-Quellen-Hierarchie

Kein veröffentlichtes Pattern hat eine **6-Quellen-Hierarchie** (Entity → Lessons → RelatedEntities → VectorSearch → DomainPattern → User), die das System autonom durchgeht. Nächster Treffer: Scrum.org „DoD for AI Agents" mit ~40% Match (statisches DoD-Set, keine Recherche-Hierarchie). Detail: [`docs/STAR.de.md`](../STAR.de.md).

### USP 3 — Aktions-Lebenszyklus PER AKTION (granular)

Knight 2506.12469 ist per User-Rolle, andere Frameworks per Tool-Klasse. Die `(a)→(e)`-Achse im Skelett koppelt an **einzelne action_kind-Telemetrie** (avg-Score über N Aktionen). Granularer, näher an SAE-Driving-Logik aber für jede Aktion separat. Detail: [`docs/LIFECYCLE.de.md`](../LIFECYCLE.de.md).

### USP 4 — Closed-Loop DoD-Erfüllung → Stufenwechsel

Knight nennt das explizit „future work". Das Skelett hat es konkret: DoD-Erfüllungsrate über N Aktionen triggert (b)→(c)→(d) Promotion, Drift triggert Demotion. Kombination DoD-rate + Auto-Demote-Logik mit Sliding-Window ist eigenständig.

### USP 5 — AUTONOMOUS-Revision-Loop mit Lesson-Feedback

Bei Validation-Verfehlung in Stage `(e)` zeichnet der Orchestrator (Phase 5.0) automatisch Lessons auf, re-derivt DoD, retried `act()` mit max-attempts-Cap. Das verbindet Phase-2-DoD-Engine + Phase-4-LessonsAggregator + Phase-3-Lifecycle in einer geschlossenen Schleife.

### USP 6 — Cross-Domain-Verifikation als executable spec

`tests/examples/test_cross_demo.py` (Phase 5.5) verifiziert automatisiert, dass drei verschiedene Demo-Domänen (architect_lite/tax_lite/cfo_lite) identische Pipeline-Counts produzieren. Wenn der Test bricht, ist die Genericity gefährdet. Domain-Unabhängigkeit ist damit testbar, nicht nur dokumentiert.

## Inspirations-Quellen

Wo das Skelett von externen Patterns Lehren gezogen hat:

| Quelle | Was übernommen | Wo im Skelett |
|---|---|---|
| Anthropic Agent Skills | YAML-Frontmatter + Markdown-Body als Entity-Container | [`Phase 1.1`](../STAR.de.md) |
| OTel-GenAI Semantic Conventions | Provenance-Schema, span-attribute-Mapping | [`Phase 4.3`](../OBSERVABILITY.de.md) |
| Letta File-Memory Benchmark | Validierung der File-First-Wahl | [`03_GEDAECHTNIS.md`](03_GEDAECHTNIS.md) |
| Knight 5-Levels Autonomy | Lifecycle-Stage-Vokabular | [`09_FRAMEWORK.md`](09_FRAMEWORK.md) |
| LangGraph `interrupt_on` | Plan-Gate als Schicht | [`Phase 3.1`](../LIFECYCLE.de.md) |
| Reflexion (Shinn 2023) | Self-Critique-Pattern (heute Phase-6+ Erweiterung) | [`06_SELF_IMPROVEMENT.md`](06_SELF_IMPROVEMENT.md) |
| Karpathy AutoResearch | M4 Korpus-vor-Pipeline-Pattern | [`08_GOLD_PATTERNS.md`](08_GOLD_PATTERNS.md) |
| Microsoft Agent-SRE | SLI-Tracking + Auto-Restriction | [`docs/LIFECYCLE.de.md`](../LIFECYCLE.de.md) Drift-Detection |

## Bewusste Nicht-Adoption

Wo verbreitete Frameworks bewusst nicht übernommen wurden:

| Framework | Warum nicht |
|---|---|
| **Letta (MemGPT)** | DB-only Memory, konfliktet File-First-Prinzip (P6) |
| **Mem0** | redundant zum Vector-Store-Layer |
| **CrewAI** | Role/Goal/Backstory-DSL bildet das Effektor-Pattern nicht sauber ab |
| **Smolagents Code-Agents** | Konkurrenz zum Self-Improvement-Loop, kein USP |
| **Flowise / Langflow / n8n** | Visual-Builder, nicht für Backend-Logik |

## Skelett vs. Konsument

| Layer | Skelett | Konsument (Phase 7+) |
|---|---|---|
| Pipeline-Orchestrierung | ✓ vollständig | nutzt Skelett |
| Effektor-Vertrag | ✓ Protocol + Base | implementiert konkrete Effektoren |
| File-Memory + Vector-Source | ✓ EntityStore + VectorSearchSource-Stub | wired echten Vector-Client |
| OTel-GenAI-Spans | ✓ struktur-only Converter | wired Exporter (Langfuse/Jaeger/etc.) |
| Plan-Gate-API | ✓ propose/approve/reject/apply | UI-Cockpit, Notification-Channel |
| Lifecycle-State-Machine | ✓ avg-Score-Transitions | per-kind-Tuning, Stage-Visibility-UI |
| Lessons-Aggregator | ✓ record + query | Lift-Tracking, Pattern-Distillation |
| EventBus | ✓ in-memory pub/sub | Cross-Process-Persistierung, Event-Routing |
| Self-Improvement-Worker | ✗ Konzept-Doku | Sandbox-Implementierung (E2B / Firecracker / Container) |

Das Skelett ist die **Anwendungs-Schicht** zwischen low-level OSS-Frameworks (LangGraph, PydanticAI, OpenTelemetry) und Domain-spezifischen Konsumenten. Es liefert ein opinionated Pattern-Set, das in einer Codebasis zusammen funktioniert — nicht ein generischer Toolkit, der alle Patterns unterstützt.

## Recherche-Quellen

Anthropic / Forschung:
- [Agent Skills (Engineering Blog)](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)
- [anthropics/skills GitHub](https://github.com/anthropics/skills)
- [Effective Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Measuring Agent Autonomy](https://www.anthropic.com/research/measuring-agent-autonomy)
- [Levels of Autonomy (arXiv 2506.12469)](https://arxiv.org/abs/2506.12469)
- [Knight Institute LoA](https://knightcolumbia.org/content/levels-of-autonomy-for-ai-agents-1)
- [Reflexion (arXiv 2303.11366)](https://arxiv.org/pdf/2303.11366)
- [Letta File-Memory Benchmark](https://www.letta.com/blog/benchmarking-ai-agent-memory)
- [Karpathy AutoResearch](https://github.com/karpathy/autoresearch)
- [CSA Agentic Trust Framework](https://cloudsecurityalliance.org/blog/2026/02/02/the-agentic-trust-framework-zero-trust-governance-for-ai-agents)

OSS-Frameworks:
- [LangGraph](https://github.com/langchain-ai/langgraph) · [HITL Docs](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)
- [PydanticAI](https://github.com/pydantic/pydantic-ai)
- [Langfuse](https://github.com/langfuse/langfuse)
- [gotoHuman](https://www.gotohuman.com/) · [HumanLayer ACP](https://github.com/humanlayer/agentcontrolplane)
- [E2B Sandbox](https://e2b.dev/) · [Daytona](https://daytona.io/) · [Modal](https://modal.com/)
- [Cognee](https://github.com/topoteretes/cognee)
- [Letta](https://github.com/letta-ai/letta) · [Mem0](https://github.com/mem0ai/mem0) · [Zep](https://www.getzep.com/)
- [Scrum.org DoD for AI Agents](https://www.scrum.org/resources/blog/definition-done-ai-agents)
- [OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/)
