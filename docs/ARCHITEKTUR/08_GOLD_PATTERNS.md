# 08 — Gold-Patterns

> Wiederkehrende Strukturen die sich quer durch die Architektur ziehen — die Hebel, die das Gesamtsystem überproportional stärken.

## Zwei Bilder, ein System

Das Skelett kann auf **zwei Leitbilder** abgebildet werden — beide sind richtig, sie beschreiben verschiedene Ebenen.

### Multi-Tool-System (Strukturbild)

N Effektoren, jeder mit eigener Logik, arbeiten semi-autonom, aber alle sind über das zentrale System verbunden. Information fließt **beidseitig** — Effektor → Zentrum (Provenance, Lessons, Traces), Zentrum → Effektor (DoD-Hints aus LessonsSource, Master-Patterns).

→ Beschreibt **wie** das System gebaut ist.

### Assistent (Erlebnisbild)

Eine Stimme, eine Persönlichkeit, eine Schnittstelle. Der User sagt was er will, das System tut den Rest — koordiniert die internen Effektoren, fragt nur dann zurück wenn es muss, antizipiert was als nächstes nötig ist.

→ Beschreibt **wie sich** das System anfühlen soll.

Heute liefert das Skelett den Multi-Tool-Teil (Komponenten + Pattern). Den Assistent-Teil (Top-Level-UI, antizipative Schicht) bauen Konsumenten obendrauf.

## Fünf Meta-Patterns die sich quer durchs System ziehen

### M1 — Pre-Lookup-Pattern

**Form**: Effektor liest **vor** der Aktion einen kontextuellen Index, der die Aktion kalibriert.

| Auftauchen | Was wird vorab geladen | Effekt |
|---|---|---|
| P1 (Steckbrief-zuerst) | Entity-Steckbrief | Sanity-Erwartungen |
| Master-Pattern-Lookup | Domain-spezifische Standards | Few-Shot-Anker |
| Few-Shot-Loop | Failure-Cases als Few-Shots | Vermeidung wiederholter Fehler |
| LessonsSource-Pull | Aktuelle Lessons | Effektor startet „klüger" |
| Entity-Cache (Konsumenten-spezifisch) | Entity-Liste | Lookups <1ms |

Realisierung im Skelett: **`Effector.pre_load(context)`** (Phase 1.3 Protocol). Effektor füllt den `context`-Dict, der dann zur DoD-Engine fließt. Konvention: orchestrator-injizierter `context["kind"]` (Phase 5.1) für LessonsSource, `context["entity_id"]` für EntityFrontmatterSource.

### M2 — Aggregations-Adapter-Pattern (Upstream)

**Form**: Effektor meldet ein typisiertes Ergebnis nach oben (Provenance, Lesson, Konflikt, Capability, Plan) — das Zentrum entscheidet was passiert.

| Was meldet ein Effektor | Empfänger | Action |
|---|---|---|
| `_provenance` block | wird an Output-Daten angehängt | nachvollziehbar machen |
| `record_lesson` | LessonsAggregator | Pattern-Promotion (Phase 6+) |
| `plan_gate.propose(kind=...)` | PlanGate | User-Approve |
| Konflikt-Detection | als Plan vorgeschlagen | Konflikt-Auflösung |
| `tool_registry.register(...)` | ToolRegistry | Cross-Effector-Lookup |

Realisierung im Skelett: **`Effector.upstream(kind, payload)`** (Phase 1.3 Protocol). Phase 5.1 verdrahtet zusätzlich automatisches Event-Publishing aus dem Orchestrator (`plan_proposed`, `lifecycle_transition`, `trace_recorded`, `lesson_recorded`).

### M3 — User-als-Gate-Pattern

**Form**: Wenn die KI eine Aktion mit Außenwirkung vorhat, hält sie inne und holt User-Bestätigung — bevor irgendwas geschrieben wird.

| Wo | Was wird gehalten | Approval-Surface |
|---|---|---|
| Plan-Gate (Stage `(b)`) | Schreibe-Aktion | extern: UI-Cockpit (Konsumenten-spezifisch) |
| Self-Improvement | Code-Patches | Plan-Gate mit `kind="code_patch"` |
| Pattern-Promotion | Neue Default-Variante | Plan-Gate mit `kind="prompt_variant_promotion"` |

Realisierung: **`Effector.gate(action) -> bool`** (Phase 1.3) als per-Action-Vorprüfung. **`PlanGate`** (Phase 3.1) als Orchestrator-Layer für stage-(b)-Approvals. Detail: [`docs/LIFECYCLE.de.md`](../LIFECYCLE.de.md).

### M4 — Korpus-vor-Pipeline-Pattern

**Form**: Vor jedem Pipeline-Tweak: Test gegen einen **Korpus** unterschiedlicher Eingabe-Stile mit erwarteten Output-Bereichen. Wenn ein Tweak den Korpus verschlechtert: nicht mergen.

Anti-Muster: Pipeline-Tweak ist auf einem Eingabe-Stil plausibel, ist auf einem anderen kaputt — Reverts sind die Folge.

Realisierung: nicht im Skelett. Korpus-Aufbau ist Domain-spezifisch (Vorgang-Stil-Sammlung, Erwartungswerte definieren, Test-Harness schreiben). Schutz gegen Drift: jeder Konsument legt seinen eigenen Korpus an, mit den Demo-Effektoren als Vorbild.

### M5 — Definition-of-Done-Pattern

**Form**: Vor jeder Aktion mit Außenwirkung recherchiert das System die Definition of Done aus 6 priorisierten Quellen. Findet es keine ausreichend klare DoD, fragt es den User mit gezielten Rückfragen — bevor es handelt.

Realisierung: **`organism.dod.DoDEngine`** (Phase 2). Detail: [`docs/STAR.de.md`](../STAR.de.md). Der M5-Pattern ist die Synthese der vier anderen:

- M1 (Pre-Lookup) liefert das Material für die DoD-Recherche
- M2 (Upstream) trägt DoD + Erfüllungsstand nach oben
- M3 (User-Gate) ist der Notausgang wenn DoD unklar bleibt
- M4 (Korpus-vor-Pipeline) ist DoD im Großen — Pipeline-Tweak bekommt nur grünes Licht wenn er DoD über alle Korpus-Eingaben erfüllt

Alle vier greifen ineinander, aber **M5 ist das verbindende Glied**, das aus „N lose Bauteile" einen Organismus macht. Ohne DoD ist das System reaktiv. Mit DoD ist es **bewertend** — es weiß ob es gut war was es getan hat, ohne dass der Mensch es ihm sagt.

## Top-3 Optimierungs-Hebel für Konsumenten

Phase 7+ (außerhalb des Skeletts):

### Hebel 1 — Generische Preflight-Schicht (M1 zentralisieren)

`pre_load`-Logik kann in einem zentralen Preflight-Service gebündelt werden, der atomar zurückgibt was ein Effektor vor Start braucht. Heute: jeder Effektor implementiert `pre_load` selbst. Möglicher Nutzen: einheitliche Caching-Strategie, gemeinsame Capabilities-Discovery.

→ Würde der Konsument als `<consumer>/services/preflight.py` bauen, übergreifend über mehrere Effektoren.

### Hebel 2 — Universeller Upstream-Bus (M2 konsolidieren)

Heute hat jeder Aggregator eine eigene Schnittstelle (`record_lesson`, `propose_plan`, etc.). Phase 5.1 hat Event-Publishing eingeführt — Konsumenten könnten einen einzigen `submit(kind, payload)`-Eingangspunkt schaffen, der intern routet.

→ Würde der Konsument als Wrapper-Layer um EventBus + LessonsAggregator + PlanGate bauen.

### Hebel 3 — Cockpit-Sidebar (M3 konsolidieren)

Plan-Gate-Decisions, Lesson-Reviews und Konflikt-Resolutionen brauchen heute getrennte UIs. Eine zentrale „Pending Actions"-Sidebar via EventBus-Subscription würde alle ausstehenden Aktionen aus allen Effektoren in einem Stream zeigen.

→ Würde der Konsument als Web-Frontend bauen, das EventBus-Events `plan_proposed`/`lifecycle_transition` konsumiert.

## Schlussbild

```
   Domäne austauschbar
        ⇡
   Bauteile (Effektor / Memory / Nervous / Observation / Lifecycle)  konstant
        ⇡
   Gold-Patterns M1 M2 M3 M4 M5  konstant
        ⇡
   Mensch im Mittelpunkt  konstant
```

Was unten konstant bleibt, ermöglicht oben das Variieren. Das ist der Vertrag.
