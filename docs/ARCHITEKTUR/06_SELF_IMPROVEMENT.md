# 06 — Self-Improvement-Loop + Reinforcement-Tracking

> Wie kann sich das System selbst weiter entwickeln? Was wird für späteres Reinforcement-Learning getrackt?

## Die Idee

Die ersten fünf Kapitel beschreiben ein System das **funktioniert, aber sich nicht selbst weiter entwickelt**. Effektoren werden besser durch Lessons (siehe [`04_LERNEN.md`](04_LERNEN.md)), aber neue Capabilities entstehen nur wenn ein Mensch Code schreibt.

Der Self-Improvement-Loop ist der Versuch, dieses Wachstum **selbst zu generieren**: das System erkennt Capability-Lücken (über Trace-Analyse), schlägt Code-Änderungen vor, gates sie durch User-Approve, deployed sie, beobachtet ob es besser wird.

Plus: alles was beobachtet wird, wird **getrackt** — als Trainingssignal für ein zukünftiges Reinforcement-Learning-Setup, das die Vorschläge selbst gewichtet.

**Skelett-Stand**: Konzept dokumentiert, **Implementation außerhalb des Skeletts** (Phase 6+). Das Skelett liefert die Bausteine (TraceStore, PlanGate, Sandbox-Pattern), Konsumenten implementieren den eigentlichen Worker.

## Die drei Komponenten des Self-Improvement-Loops

### Queue (Detection)

Sammelt **Capability-Lücken** aus den vorhandenen Datenquellen:

- TraceStore-Einträge mit Failure-Status (ActionStatus.DENIED oder Validation `all_satisfied=False`)
- Insight-Anfragen die mit „weiß nicht" beantwortet wurden
- User-Korrekturen mit „war keine bekannte Klassifikation"

Lücken werden geclustert (welche kommen mehrmals vor), priorisiert (wie oft, wie kürzlich).

### Worker (Patch-Generation)

Greift einen Cluster, baut einen Few-Shot-Loop (siehe [`04_LERNEN.md`](04_LERNEN.md)):

1. Liest umgebenden Code
2. Schreibt einen Patch-Vorschlag (LLM-Aufruf)
3. Lässt Tests laufen (in Sandbox)
4. Iteriert (max N, max M Tokens)

**Sandbox-Anforderung**: Worker läuft in **isolierter Umgebung** (z.B. Container, Firecracker-VM, ephemeral VM-Instance), nicht in der gleichen Process-Boundary wie das Hauptsystem. Ein bösartiger Patch darf das System nicht beschädigen.

### Scheduler (Triggering)

Triggert Worker manuell oder periodisch wenn Capability-Lücken-Cluster über Schwelle.

## Was Self-Improvement NICHT ist

- Kein autonomer Agent. Jeder Code-Change geht durchs Plan-Gate (`kind="code_patch"` oder Äquivalent).
- Kein Replacement für CI. Tests laufen, aber Mensch entscheidet über Merge.
- Kein „selbstmodifizierender Algorithmus". Der Algorithmus ändert sich nicht, nur Code drum herum.
- Keine LLM-Auto-Approve. Plan-Gate ist **menschen-gated**.

## Reinforcement-Tracking — was wird beobachtet

Der `TraceStore` (Phase 4.1) bietet bereits die Datenquelle. Jede orchestrator-execute-Aktion landet als Trace mit:

- `kind`, `request_summary`, `context_keys`
- `dod` (mit confidence, criteria_count)
- `validation` (mit score, all_satisfied, unsatisfied)
- `transition_to` (Stage-Übergang falls passiert)
- `revision_pending` / `revision_attempts`
- `provenance` (author, timestamp)
- `started_at` / `completed_at` (Latenz-Messung)

Plan-Gate-Decisions (Phase 3.1):

- `proposed_at`, `decided_at`, `decided_by`, `decision_reason`
- `status` (PROPOSED → APPROVED/REJECTED/APPLIED)

Lessons (Phase 4.2):

- `kind`, `observation`, `criteria_hint`, `confidence_delta`, `context_pattern`

EventBus-Stream (Phase 5.1):

- Sequenzen von `plan_proposed` → `lifecycle_transition` → `trace_recorded` → `lesson_recorded` lassen sich zu Action-Sequences verketten.

## Wie das RL-Signal aussieht

Ein einzelner Trace-Eintrag ist kein RL-Signal. Was RL-tauglich macht:

1. **Reward-Definition**:
   - `validation.all_satisfied=True` und keine User-Korrektur → +1
   - `validation.all_satisfied=False` ohne Revision-Erfolg → -1
   - User-Edit mit `ratio<0.85` → -0.3 (KI war daneben)
   - Plan-Gate `REJECTED` → -1
   - Plan-Gate `APPROVED` ohne nachträgliche Korrektur → +1

2. **Sequenz**: Trace-Einträge werden zu Sequenzen verknüpft. Eine externe-Quelle-Aktion löst Effektor A aus, das löst Effektor B aus, das löst Effektor C aus — eine Sequenz mit einem aggregierten Reward am Ende.

3. **Aktion-Raum**: heute nicht als RL-Aktion modelliert, sondern als „welcher Effektor gewählt", „welche Capability mit welchen Parametern".

## Was bewusst nicht gemacht wird

- **Kein Online-Reinforcement** (Modell-Update zur Laufzeit). RL-Signale werden gesammelt, aber kein Modell direkt trainiert.
- **Kein Cloud-Training**. Daten bleiben on-prem (passt zu file-first-Memory-Prinzip aus [`00_LEITBILD.md`](00_LEITBILD.md)).
- **Keine intelligenten Belohnungen die das System sich selbst gibt**. Reward kommt aus User-Aktion oder Validation, nicht aus Selbstbewertung.

## Vision

> Das System schlägt von alleine eine bessere Antwort vor, weil es aus 10.000 vorherigen Anfragen weiß welcher Effektor-Pfad zur richtigen Antwort führt. Der User merkt nicht, dass es lernt. Er merkt nur, dass es schneller das richtige sagt.

Das setzt voraus:

- Trace-Volumen ausreichend
- Reward-Signal sauber (User-Aktionen müssen approve/reject erfasst werden, nicht implicit „die Session ist noch offen")
- Aktionsraum klar (Effektor-Capability-Combo)
- Modell-Setup (kommt in einer eigenen Phase nach Sandbox-Stabilität)

## Was im Skelett heute praktisch funktioniert

Skelett-Stand (Phase 4.1+5.1):

- TraceStore ist live (`organism.observability.TraceStore`), schreibt bei jedem `orchestrator.execute()` und `apply_approved_plan()`.
- Plan-Gate-Approve/Reject getrackt (Phase 3.1).
- Lesson-Aufzeichnung läuft (Phase 4.2).
- AUTONOMOUS-Revision-Loop (Phase 5.0) zeichnet Failure-Reasons als Lessons auf.
- EventBus-Streams (Phase 5.1) für Sequenz-Verkettung.

Was als „Reinforcement" bezeichnet wird ist heute **telemetrie-getriebene Heuristik-Verbesserung**. Der Sprung zu echtem RL kommt erst wenn:

1. Reward-Lücken geschlossen (Konsumenten-Verantwortung: User-Aktion-Capture in UI)
2. Sandbox-Implementation für Self-Improvement-Worker fertig (extern, nicht im Skelett)
3. Aktionsraum sauber faktorisiert (Tool-Capability-Schema-Standard)

Bis dahin: das Skelett-Setup ist **RL-ready**, aber nicht RL-aktiv.

## Verweise

- Konzept Lifecycle (a)→(e): [`09_FRAMEWORK.md`](09_FRAMEWORK.md), [`docs/LIFECYCLE.de.md`](../LIFECYCLE.de.md)
- Lessons + 3 Lern-Schleifen: [`04_LERNEN.md`](04_LERNEN.md)
- Trace + Provenance + Events: [`docs/OBSERVABILITY.de.md`](../OBSERVABILITY.de.md)
