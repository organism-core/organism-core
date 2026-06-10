# 10 — Landschaft

> Wo steht das Skelett im breiteren Ökosystem? Was ist differenzierend, was ist Mainstream geworden?
> **Stand: 2026-06-10** (Landschafts-Check mit Web-Research; Vorstand 13.05. — alle großen Wetten haben gewonnen oder sind Mainstream geworden. Kurs bestätigt, Karte aktualisiert.)

## Kernbotschaft (neu seit Juni 2026)

**Die Integration ist der USP, nicht die Primitive.** Einzelbausteine
(HITL-Gates, File-Memory, Rubric-Validierung) sind 2026 Commodity oder
auf dem Weg dahin. Was als Gesamtsystem weiterhin niemand shippt:
**DoD-Recherche → Gate → verdiente Autonomie → Validierung →
persistente cross-arm Lessons in EINEM Execution-Pfad.**

## Mainstream-Alignment

Das Skelett bewegt sich im Strom, nicht exotisch. Konvergent
branchenweit entwickelt:

- **File-First-Memory mit YAML+Markdown** — inzwischen
  **Mainstream-Default**: Letta MemFS (04/26), Claude Auto-Memory
  (03/26), Hermes Agent USER.md/MEMORY.md, SKILL.md als
  Industriestandard. Validiert unsere Wahl; kein Differenzierer mehr.
- **Provenance-Pflicht** — OTel GenAI Semantic Conventions (weiterhin
  offiziell „Development", NICHT stable — Baseline pinnen, eigene
  Felder als Namespace-Attribute, nicht als `gen_ai.*`-Forks).
- **Plan-Gate / HITL** — **vollständige Commodity**: OpenAI
  `needsApproval`+interruptions, LangGraph interrupts, MS
  ToolApprovalAgent, Google ADK ToolConfirmation, CrewAI
  Enterprise-HITL, Claude SDK Permissions. Dazu macht der **EU AI Act
  Art. 14** menschliche Aufsicht zur Compliance-Pflicht.
  Differenzierung nur noch über Spezifik: **Plan-Objekte mit Diff auf
  die File-Wahrheit** statt generischem Tool-Call-Approval.
- **Rubric-Validierung** — LangChain deepagents **RubricMiddleware**
  (02.06.26) und MS Foundry **Auto-Rubrics** (03.06.26) shippen
  Teile des DoD-Patterns; Anthropic **Outcomes** (Beta 06.05.26)
  bleibt der nächste Verwandte. Niemand kombiniert auto-derivierte
  Rubrics aus einer Quellen-Hierarchie mit verdienten
  Autonomie-Stufen.

## Was differenziert (Stand Juni 2026, adversarial geprüft)

### 1 — Persistente Cross-Arm-Lessons (hat niemand first-class)

Verfehlungs-Erkenntnisse werden destilliert, persistiert und beim
nächsten Derive **über Aktionstypen hinweg** zurückverteilt
(`LessonsSource` + `CrossDomainLessonsSource`, das
Dreaming-Äquivalent). Anthropic Dreaming ist Research-Preview;
strukturierte, konfigurierbare cross-arm Verteilung als
Framework-Primitiv shippt niemand.

### 2 — Score-Autonomie pro Aktionstyp, mit Auto-Demotion

Die `(a)→(e)`-Achse koppelt an **einzelne action_kind-Telemetrie**
(avg-Score, Sliding-Window). Literatur-Stützung: „The Digital
Apprentice" (arXiv 2606.04321, 03.06.26) beschreibt per-Skill-Tiers
mit Promotion als Kompetenz-Evidenz und Auto-Demotion — **reine
Konzeption, kein Code**; wir sind dem geshippten Stand voraus.
**Auto-Demotion ist dabei ein Security-Feature**: Revocability —
verliehene Autonomie wird bei Drift automatisch entzogen — adressiert
direkt die OWASP Agentic Top 10 (2026), die exzessive, nicht
widerrufbare Agent-Autonomie als Kernrisiko führen. Detail:
[`docs/LIFECYCLE.md`](../LIFECYCLE.md).

### 3 — DoD-Recherche als 6-Quellen-Hierarchie (Halbwertszeit: Monate)

Kein veröffentlichtes Framework geht autonom eine priorisierte
Quellen-Hierarchie durch (Entity → Lessons → RelatedEntities →
VectorSearch → DomainPattern → User). Ehrlich datiert: MS Foundry
generiert Rubrics automatisch (eval-seitig), deepagents iteriert
gegen developer-provided Rubrics — die **Kombination** beider wäre
unser Pattern und ist absehbar. Der Vorsprung ist real, aber in
Monaten zu messen, nicht in Jahren. Detail:
[`docs/STAR.md`](../STAR.md).

### 4 — Genericity-Guard als Architektur-Fitness-Function

`tests/examples/test_cross_demo.py` erzwingt identische
Pipeline-Counts über drei Demo-Domänen. **Ehrliche Einordnung**
(korrigiert): das ist kein „USP gegenüber LangGraph" — generische
Frameworks sind per Konstruktion domain-frei. Es ist unsere
**Disziplin beim Generalisieren AUS einer Domäne**: eine
Fitness-Function, die Domänen-Leakage beim Weiterbau sofort sichtbar
macht. Hat niemand; kategorial Hygiene, nicht Markt-Claim.

### Eingeholt / gefallen (ehrlich dokumentiert)

- **Closed-Loop Validierung+Retry** (~70 % gefallen): deepagents
  RubricMiddleware = Validierung gegen Kriterien + Feedback + Retry;
  Outcomes = Rubric+Grader+Iterate. Rest-Differenzierung ist Punkt 1
  (persistente cross-arm Verteilung).
- **AUTONOMOUS-Revision mit Lesson-Feedback**: Richtung bestätigt
  (Hermes Skill-Self-Generation, Voyager-Loops Standard), als
  Allein-Claim eingeholt.
- **File-First-Memory**: Mainstream (siehe oben).
- **Plan-Gate-HITL**: Commodity (siehe oben) — als Baustein nennen,
  nicht als USP.

## Forschungs-Rückenwind

- **„The moat moved to the harness"** (Konsens 2026, PostTrainBench):
  Agenten mit Autonomie über eigenes Training erreichen 23.2 % und
  reward-hacken. Explizite Harness-Loops mit Verifiern schlagen
  Weight-Level-Selbstverbesserung — exakt die Skelett-Wette
  (explizite Lifecycle-Stufen statt RL-Finetuning).
- **GER-Eval (arXiv 2602.08672)**: selbst-abgeleitete Rubrics
  degradieren in wissensintensiven Domänen. Konsequenz als
  **Evaluator-Leitlinie**: DoD-Checks **mechanisch/code-basiert wo
  möglich** (`evaluator="rule"`), LLM-Judge nur wo qualitativ nötig;
  periodische Kalibrierung KI-Score vs. User-Urteil einplanen.
  Unsere Gegenmittel (Quellen-Grounding + User-Rückfrage als
  Quelle 6) sind genau richtig.
- **Memory-Gegenwind an den Rändern**: Markdown-Decay,
  ~200-Zeilen-Attention-Limit pro Regel-File, Memory-Poisoning in
  den OWASP Agentic Top 10. Konsequenz im Repo selbst umgesetzt:
  Journal als Index + Topic-Files ≤200 Zeilen.

## Standards-Lage (Protokollkriege entschieden)

- **MCP + A2A haben gewonnen.** MCP seit 12/25 bei der Linux
  Foundation (Agentic AI Foundation; Anthropic+OpenAI+Block), A2A
  v1.0 stable (150+ Orgs); ACP in A2A gemergt, AGNTCY in LF
  aufgegangen. Unsere Adapter-Wetten = das Gewinner-Paar.
- **MCP-RC final 2026-07-28**: stateless Kern, Roots/Sampling/Logging
  deprecated, Tasks graduiert. Bindende Constraints für jeden
  künftigen Adapter: [`docs/MCP_DESIGN.md`](../MCP_DESIGN.md)
  (Audit-Ergebnis: kein MCP-Code im Skelett — nichts bricht).
- **HITL hat keinen Cross-Vendor-Standard.** Einziger
  Protokoll-Kandidat: MCP Elicitation. Chance (Design-Notiz, nicht
  bauen): Plan-Gate als Elicitation exponieren — dann ist unser Gate
  für fremde MCP-Clients sichtbar.
- **OpenAI beerdigt Agent Builder + Evals** (Shutdown 30.11.26) —
  nichts darauf bauen; validiert „Verification als Produkt" und
  öffnet OSS-Bedarf für Validierungs-Harnesses.
- **Observability**: Langfuse → ClickHouse (bleibt OSS/self-hostable
  — unser Stub bleibt richtig); Konvergenz auf OTel-Ingestion.

## Inspirations-Quellen

| Quelle | Was übernommen | Wo im Skelett |
|---|---|---|
| Anthropic Agent Skills | YAML-Frontmatter + Markdown-Body als Entity-Container | [`Phase 1.1`](../STAR.md) |
| Anthropic Outcomes (Beta 05/26) | Begriffs-Mapping Rubric↔DoD, Separator-Pattern, `failed` vs `exhausted` | [`TRANSLATION_DICTIONARY.md`](../TRANSLATION_DICTIONARY.md), Phase 8A |
| OTel-GenAI Semantic Conventions | Provenance-Schema, span-attribute-Mapping (Baseline gepinnt, „Development") | [`Phase 4.3`](../OBSERVABILITY.md) |
| Letta File-Memory Benchmark / MemFS | Validierung der File-First-Wahl | [`03_GEDAECHTNIS.md`](03_GEDAECHTNIS.md) |
| Knight 5-Levels Autonomy | Lifecycle-Stage-Vokabular | [`09_FRAMEWORK.md`](09_FRAMEWORK.md) |
| „The Digital Apprentice" (arXiv 2606.04321) | Literatur-Stützung per-Skill-Tiers + Auto-Demotion | [`docs/LIFECYCLE.md`](../LIFECYCLE.md) |
| Spec Kit Agents (arXiv 2604.05278) | Evidenz-Grounding vor Aktion (1 Quelle; engster DoD-Verwandter) | [`docs/STAR.md`](../STAR.md) |
| LangGraph `interrupt_on` | Plan-Gate als Schicht | [`Phase 3.1`](../LIFECYCLE.md) |
| LangChain deepagents RubricMiddleware (06/26) | Datierung des Closed-Loop-Felds | dieses Kapitel |
| Reflexion (Shinn 2023) | Self-Critique-Pattern | [`06_SELF_IMPROVEMENT.md`](06_SELF_IMPROVEMENT.md) |
| Karpathy AutoResearch | M4 Korpus-vor-Pipeline-Pattern | [`08_GOLD_PATTERNS.md`](08_GOLD_PATTERNS.md) |
| Microsoft Agent-SRE | SLI-Tracking + Auto-Restriction | [`docs/LIFECYCLE.md`](../LIFECYCLE.md) Drift-Detection |
| GER-Eval (arXiv 2602.08672) | Evaluator-Leitlinie: mechanisch > LLM-Judge | dieses Kapitel + [`docs/STAR.md`](../STAR.md) |

## Bewusste Nicht-Adoption

| Framework / Quelle | Warum nicht |
|---|---|
| **Letta (MemGPT)** | DB-only Memory, konfliktet File-First-Prinzip (P6) |
| **Mem0** | redundant zum Vector-Store-Layer |
| **CrewAI** | Role/Goal/Backstory-DSL bildet das Effektor-Pattern nicht sauber ab |
| **Smolagents Code-Agents** | Konkurrenz zum Self-Improvement-Loop, kein USP |
| **Flowise / Langflow / n8n** | Visual-Builder, nicht für Backend-Logik |
| **Hermes Agent (Nous)** | Self-evolving Single-Agent — komplementär; läuft als Effektor AUF dem Skelett, nicht statt seiner |
| **Hyperagent-artige Self-Modification** | Wir bleiben bewusst eine Schicht darunter: Substrat, menschen-kuratierte Patterns (PostTrainBench-Argument) |
| **OpenAI Agent Builder / Evals** | Shutdown 30.11.26 angekündigt — keine Abhängigkeit |
| **Temporal / Restate (durable workflows)** | Vendor-Footprint, untergräbt Plan-Gate-als-Vertrag (siehe [`docs/REENTRANCE.md`](../REENTRANCE.md)) |

## Skelett vs. Konsument

| Layer | Skelett | Konsument |
|---|---|---|
| Pipeline-Orchestrierung | ✓ vollständig | nutzt Skelett |
| Effektor-Vertrag | ✓ Protocol + Base | implementiert konkrete Effektoren |
| File-Memory + Vector-Source | ✓ EntityStore + chromadb-duck-typed Adapter | wired echten Vector-Client |
| OTel-GenAI-Spans | ✓ struktur-only Converter | wired Exporter (Langfuse/Jaeger/etc.) |
| Plan-Gate-API | ✓ propose/approve/reject/apply | UI-Cockpit, Notification-Channel |
| Lifecycle-State-Machine | ✓ avg-Score-Transitions + Auto-Demotion | per-kind-Tuning, Stage-Visibility-UI |
| Lessons-Aggregator | ✓ record + query + cross-kind | Lift-Tracking, Pattern-Distillation |
| EventBus | ✓ in-memory pub/sub | Cross-Process-Persistierung, Event-Routing |
| Self-Improvement-Worker | ✗ Konzept-Doku | Sandbox-Implementierung (E2B / Firecracker / Container) |

Das Skelett ist die **Anwendungs-Schicht** zwischen low-level
OSS-Frameworks (LangGraph, PydanticAI, OpenTelemetry) und
domain-spezifischen Konsumenten: ein opinionated Pattern-Set, das in
einer Codebasis zusammen funktioniert — der Harness, nicht das Modell
und nicht der Visual-Builder.

## Recherche-Quellen

Stand 13.05. (Basis):
- [Agent Skills (Engineering Blog)](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) · [anthropics/skills](https://github.com/anthropics/skills)
- [Effective Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Measuring Agent Autonomy](https://www.anthropic.com/research/measuring-agent-autonomy)
- [Levels of Autonomy (arXiv 2506.12469)](https://arxiv.org/abs/2506.12469) · [Knight Institute LoA](https://knightcolumbia.org/content/levels-of-autonomy-for-ai-agents-1)
- [Reflexion (arXiv 2303.11366)](https://arxiv.org/pdf/2303.11366)
- [Letta File-Memory Benchmark](https://www.letta.com/blog/benchmarking-ai-agent-memory)
- [Karpathy AutoResearch](https://github.com/karpathy/autoresearch)
- [CSA Agentic Trust Framework](https://cloudsecurityalliance.org/blog/2026/02/02/the-agentic-trust-framework-zero-trust-governance-for-ai-agents)
- [LangGraph](https://github.com/langchain-ai/langgraph) · [HITL Docs](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)
- [PydanticAI](https://github.com/pydantic/pydantic-ai) · [Langfuse](https://github.com/langfuse/langfuse)
- [gotoHuman](https://www.gotohuman.com/) · [HumanLayer ACP](https://github.com/humanlayer/agentcontrolplane)
- [E2B Sandbox](https://e2b.dev/) · [Daytona](https://daytona.io/) · [Modal](https://modal.com/)
- [Cognee](https://github.com/topoteretes/cognee) · [Letta](https://github.com/letta-ai/letta) · [Mem0](https://github.com/mem0ai/mem0) · [Zep](https://www.getzep.com/)
- [Scrum.org DoD for AI Agents](https://www.scrum.org/resources/blog/definition-done-ai-agents)
- [OTel GenAI Semconv](https://opentelemetry.io/docs/specs/semconv/gen-ai/)

Update 10.06. (Landschafts-Check):
- LangChain deepagents RubricMiddleware (02.06.26) — langchain.com/blog/introducing-rubrics-for-deepagents
- MS Foundry Auto-Rubric + Agent Optimizer (Build, 03.06.26) — devblogs.microsoft.com/foundry/
- „The Digital Apprentice" (arXiv 2606.04321, 03.06.26)
- Spec Kit Agents (arXiv 2604.05278) · GER-Eval (arXiv 2602.08672)
- MCP-RC (final 28.07.26) — blog.modelcontextprotocol.io · AAIF/Linux Foundation (12/25)
- A2A v1.0, 150+ Orgs — linuxfoundation.org (04/26)
- Anthropic Outcomes Beta (06.05.26) — platform.claude.com/cookbook
- OpenAI Evals/Agent-Builder-Shutdown 30.11.26 — developers.openai.com/api/docs/deprecations
- Hermes Agent — github.com/nousresearch/hermes-agent (25.02.26)
- PostTrainBench — via agyn.io/blog/ai-self-improvement-2026
- Letta MemFS (04/26) — letta.com/blog/letta-code
- OWASP Agentic Top 10 2026 / Memory-Poisoning — via matrixorigin.io/blog/markdown-agent-memoria
- Langfuse → ClickHouse (16.01.26)
