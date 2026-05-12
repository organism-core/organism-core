*[🇬🇧 English version](M5_WHITEPAPER.md)*

# M5 — Definition-of-Done als Recherche-Engine

> Ein Pattern für selbstbewertende Multi-Tool-Systeme.
> Whitepaper-Draft, Stand: 2026-05-10 (nach Phase 6.4).
> Detail-Vertiefungen in [`STAR.de.md`](STAR.de.md), [`LIFECYCLE.de.md`](LIFECYCLE.de.md), [`OBSERVABILITY.de.md`](OBSERVABILITY.de.md), [`DEMOS.de.md`](DEMOS.de.md).

## Abstract

Multi-Tool-Systeme mit autonomen Aktionen leiden an einer impliziten Lücke: **was ist eine „korrekte" Aktion?** Tests prüfen Code, der Mensch korrigiert reaktiv, der LLM-Konfidenzwert ist selbstreferentiell. M5 schließt diese Lücke durch eine zweiteilige Regel:

> **Vor jeder Aktion mit Außenwirkung recherchiert das System die Definition of Done aus 6 priorisierten Quellen. Findet es keine ausreichend klare DoD, fragt es den User mit gezielten Rückfragen — bevor es handelt. Nach der Aktion misst es die Erfüllung der DoD und schreibt das Ergebnis zurück ins Gedächtnis.**

Der zweite Satz ist die wichtigere Hälfte: DoD ist nicht nur Vor-Recherche, sondern auch Nach-Bewertung. Erst durch das geschlossene Loop wird das System **bewertend** statt nur reaktiv — und durch das Aufschreiben der Verfehlungs-Lessons **selbst-korrigierend**.

Die DoD-Recherche-Engine ist der Kern eines Pattern-Sets, das aus 5 Komponenten (Effektoren, Memory, Nervous-System, Observation, Lifecycle) und 5 Meta-Patterns (M1 Pre-Lookup, M2 Upstream, M3 User-Gate, M4 Korpus-vor-Pipeline, M5 DoD) besteht. M5 ist das verbindende Glied, das aus losen Bauteilen einen Organismus macht — das System wird **bewertend** statt nur reaktiv.

Eine Reference-Implementation liefert das Pattern in 503 Tests grün, ein automatisierter Cross-Domain-Test verifiziert die Domänen-Unabhängigkeit über drei verschiedene Demo-Domains (Architekturbüro, Steuerberatung, CFO-Office) mit identischen Pipeline-Counts.

## 1. Motivation

In jedem Multi-Tool-System mit autonomen Akteuren entsteht die Frage: woran misst man, ob eine Aktion korrekt war? Klassische Erfolgs-Maßstäbe greifen nicht weit genug:

- **Tests laufen** prüft Code-Korrektheit, nicht Aktions-Korrektheit. Ein Effektor, der in seinen Unit-Tests grün ist, kann trotzdem in einer konkreten Domain die falsche Antwort geben.
- **Mensch korrigiert nachträglich** ist reaktiv. Die KI hat schon gehandelt, der User merkt den Fehler beim Sichten, das System lernt langsam.
- **Konfidenzwert vom LLM** ist selbstreferentiell. „Ich bin mir zu 92% sicher" sagt nichts über die externe Korrektheit aus.

M5 schließt diese Lücke durch ein einfaches, aber wirkungsstarkes Prinzip: **die Erfolgs-Kriterien werden vor der Aktion explizit gemacht**, recherchiert aus mehreren Quellen, in fester Hierarchie. Die KI handelt nur, wenn sie eine ausreichend klare DoD hat — sonst fragt sie zurück. Nach der Aktion wird die Erfüllung gemessen, das Ergebnis als Lesson zurückgeschrieben.

Das macht das System **bewertend**: es weiß, ob es gut war, was es getan hat, ohne dass der Mensch es ihm sagt. Verfehlungen werden nicht stillschweigend hingenommen, sondern als Lessons aufgeschrieben — die bei der nächsten DoD-Recherche wieder auftauchen und das System Schritt für Schritt **selbst-korrigierend** machen.

## 2. Architektur-Kontext

M5 lebt in einem System mit fünf Bauteilen und fünf Patterns:

```
   Domäne austauschbar
        ⇡
   Bauteile ① Effektoren ② Memory ③ Nervous-System ④ Observation ⑤ Lifecycle
        ⇡
   Gold-Patterns M1 Pre-Lookup, M2 Upstream, M3 User-Gate, M4 Korpus-vor-Pipeline, M5 DoD
        ⇡
   Mensch im Mittelpunkt
```

### Bauteile

- **① Effektoren** — Werkzeuge, die in die Welt greifen. Implementieren das 5-Kontakt-Protokoll (`pre_load`, `define_done`, `act`, `upstream`, `gate`).
- **② Memory** — Wahrheits-Speicher. File-first (YAML+Markdown), keine DB als kanonische Quelle.
- **③ Nervous-System** — Koordinations-Schicht (DoD-Engine, Validator, PlanGate, LifecycleManager, Orchestrator).
- **④ Observation** — Beobachtung (TraceStore, LessonsAggregator, EventBus, OTel-Converter, Provenance).
- **⑤ Lifecycle** — State-Machine pro Action-Kind: `(a) MANUAL → (b) PROPOSED → (c) CHECKED → (d) ROUTINE → (e) AUTONOMOUS`.

### Meta-Patterns

- **M1 Pre-Lookup** — Effektor liest Kontext (Steckbrief, Lessons, Master-Patterns) **vor** der Aktion.
- **M2 Upstream** — Effektor meldet typisierte Ergebnisse (Provenance, Lesson, Konflikt, Plan) nach oben.
- **M3 User-Gate** — Schreibaktionen mit Außenwirkung halten inne und holen User-Bestätigung.
- **M4 Korpus-vor-Pipeline** — Pipeline-Tweaks werden gegen einen Korpus geprüft, bevor sie deployed werden.
- **M5 DoD** — vor jeder Aktion wird die Definition of Done recherchiert und nach der Aktion validiert.

M5 ist **die Synthese der vier anderen**: M1 liefert das Material für die DoD-Recherche, M2 trägt DoD und Erfüllungsstand nach oben, M3 ist der Notausgang wenn DoD unklar bleibt, M4 ist DoD im Großen.

## 3. Die DoD-Recherche-Engine

### Stern-Topologie

Sechs Quellen liegen radial um die Aktion. Die Aktion ist das Zentrum, jede Quelle ein Strahl:

```
                     (1) EntityFrontmatter
                              │
        (2) Lessons ────┐     │     ┌──── (3) RelatedEntities
                        │     ▼     │
                       ┌─────────────┐
                       │  [ ACTION ] │
                       └─────────────┘
                        │     ▲     │
        (5) DomainPattern ────┘     └──── (4) VectorSearch
                              │
                              ▼
                  (6) UserClarification (terminal)
```

Engine evaluiert in **fester Priorität 1→6** und stoppt früh, sobald DoD klar ist (`confidence ≥ threshold` UND `clarification_needed empty`).

### Die sechs Quellen

| # | Quelle | Was sie beiträgt |
|---|---|---|
| 1 | `EntityFrontmatterSource` | Deklarierte DoD-Kriterien aus dem `frontmatter.dod`-Block der referenzierten Entity |
| 2 | `LessonsSource` | Was wurde früher als „fertig" akzeptiert (User-Korrekturen, AUTONOMOUS-Revision-Lessons) |
| 3 | `RelatedEntitiesSource` | Cross-Reference: ähnliche Entities mit DoD-Hinweisen |
| 4 | `VectorSearchSource` | Semantische Suche in Wissensbasis (Normen, Standards, Vorlagen) |
| 5 | `DomainPatternSource` | Domain-Standards und Master-Patterns |
| 6 | `UserClarificationSource` | Terminale Rückfrage wenn 1-5 nicht reichen |

### Die Reihenfolge ist domänen-unabhängig begründet

- **Spezifisch+konkret zuerst** (Entity > Related > Vector > Pattern): wer eine Antwort in der konkreten Entity findet, fragt nicht beim Vector-Store.
- **Erprobtes vor Normativem** (Lessons > Vector): Tool-eigene Lessons schlagen normative Texte, weil sie auf realen Praxisfällen basieren.
- **Normatives vor Fragendem** (1-5 > User): Normen schlagen User-Frage, weil der User seine Zeit nicht für Bekanntes verbrennen will.

Wer die Reihenfolge umkehrt, fragt den User Sachen die schon im Frontmatter stehen — das verbrennt User-Vertrauen.

### Datentypen

```
Criterion           name, expected, weight, source
SourceContribution  source_name, criteria, confidence_delta,
                    clarifications, evidence
DoD                 criteria, clarification_needed, confidence,
                    evidence_sources, _provenance
                    .is_satisfied_for_act() :: bool
```

### Zwei verschiedene Konfidenz-Größen — bitte nicht verwechseln

M5 unterscheidet **zwei orthogonale** Größen, die beide mit „Konfidenz/Score" benannt werden könnten:

| Größe | Ort | Bedeutung |
|---|---|---|
| **Definition-Confidence** | `DoD.confidence` (vor `act()`) | Wie sicher ist das System, dass die DoD selbst gut formuliert ist? Steigt mit jeder Source-Contribution; sum-capped `[0,1]`. Steuert Early-Stop und das User-Frage-Trigger (UC-Source). |
| **Fulfillment-Score** | `ValidationResult.score` (nach `act()`) | Wie gut wurde die DoD erfüllt? Gewichtete Quote der erfüllten Kriterien. Steuert Lifecycle-Stage-Transitions. |

Eine **gut definierte DoD mit hoher Definition-Confidence** kann nach der Aktion einen **niedrigen Fulfillment-Score** haben — das ist der Normal-Fall einer klar erkannten Verfehlung. Eine **schlecht definierte DoD** (niedrige Definition-Confidence) sollte gar nicht erst zur Ausführung gelangen — dann triggert der UC-Pfad (`clarification_needed`) und die Aktion wartet auf User-Klärung.

Diese Trennung ist zentral fürs Verständnis: M5 bewertet **zweimal** (Vor: ist die DoD klar genug? Nach: wurde sie erfüllt?), nicht einmal.

### Engine-Algorithmus

```
derive(request, context):
    dod = DoD.empty()
    ctx = dict(context)              # copy gegen Source-Pollution
    for source in self.sources:                     # priority order
        contribution = source.contribute(request, ctx, dod)
        merge(dod, contribution)
        if dod.confidence >= threshold AND
           not dod.clarification_needed:
            break                                   # early-stop
    return dod
```

**Merge-Regeln**:
- Criteria angefügt, mit `source` per `dataclasses.replace` gestempelt
- Confidence sum-capped auf `[0, 1]`
- Clarifications angefügt, order-preserving
- Provenance: `source_name → list[criterion_name]`

**Early-Stop-Bedingung** ist konjunktiv: confidence-threshold UND keine offenen Klärungen. Andernfalls können nachfolgende Quellen die Klärung füllen oder die Confidence erhöhen.

Detail: [`STAR.de.md`](STAR.de.md).

### Wann DoD-Recherche verzichtbar ist

Die naive Heuristik „Lesen ist OK, Schreiben braucht DoD" greift zu kurz — eine Vector-Suche ist Lesen, hat aber sehr wohl Erfolgs-Kriterien (Top-N relevant). Schärfere Heuristik:

- **Verzichtbar** bei **deterministischen** Operationen ohne Interpretationsspielraum (SQL-Lookup, Datei-Read, exakter Schema-Match)
- **Verzichtbar** in Stage `(a) MANUAL` — wenn der Mensch tut, weiß er's selbst
- **Pflicht** bei **probabilistischen** Operationen, auch lesenden (Vector-Search-Ranking, Klassifikation, OCR, KI-basierte Extraktion)
- **Pflicht** ab Stage `(b) PROPOSED` — sobald das System vorschlägt, gehört ein Erfolgs-Maßstab dazu
- **Pflicht** bei jeder Schreibaktion in den Wahrheits-Speicher
- **Pflicht** bei Code-Patches via Self-Improvement-Loop

## 4. Validator und Comparator-Semantik

Nach `act()` prüft `DoDValidator` das Ergebnis gegen die DoD. Hybrid-Comparator-Strategie unterstützt beide DoD-Definitionswege (Frontmatter-deklariert und in-code):

| Form | Beispiel | Wann | Bedeutung |
|---|---|---|---|
| `callable` | `lambda v: v > 0` | in-code DoDs | invoked, `bool()` gecastet |
| `"lo..hi"` | `"25..35"` | YAML/Frontmatter | inklusiver numerischer Range |
| `">=N"` etc | `">=90%"`, `"<5"` | YAML/Frontmatter | Schwellwert (`>=`, `<=`, `>`, `<`), optional `%`-Suffix |
| anything | `True`, `42`, `"approved"` | beide Wege | Equality (`==`) |

**Score** = `sum(weight if satisfied) / sum(all weights)` ∈ `[0, 1]`.

**Konventionen**:
- `%`-Suffix wird beidseitig gestrippt (User verantwortlich für konsistente Skala)
- Bool im numerischen Kontext explizit abgewiesen (Python-bool ist int-Subklasse, sonst würde `True == 1` Range-Tests verfälschen)
- Callable-Exceptions werden gefangen, Kriterium gilt als unsatisfied
- Missing key vs explicit None unterschieden

## 5. M5 + Lifecycle: Reife maschinen-bewertbar

Der Aktions-Lebenszyklus `(a)→(e)` wird **erst durch DoD maschinen-bewertbar**:

| Stufe | Wer prüft DoD | Konsequenz |
|---|---|---|
| (a) MANUAL | Mensch tut, kein DoD nötig | — |
| (b) PROPOSED | System schlägt vor + zeigt DoD; Mensch bestätigt | Plan-Gate-Eintrag enthält DoD |
| (c) CHECKED | System tut + checkt selbst gegen DoD; Mensch validiert | DoD-Verfehlung → User-Hinweis |
| (d) ROUTINE | System tut + Auto-Check; Mensch stichprobenhaft | Drift triggert Rückfall nach (c) |
| (e) AUTONOMOUS | System tut + Auto-Check + Revision | Mensch nur bei Anomalie |

### Stage-Transitions sind avg-Score-getrieben

```
record_outcome(kind, plan_id?, score):
    state.recent_outcomes.append({plan_id, score, recorded_at})
    if len > window_size: trim
    transition = evaluate_transition(state)
    if transition:
        state.stage = transition.to_stage
        state.recent_outcomes = []           # Frischstart
        state.transition_history.append(transition)
    persist(state)
```

- **Promote**: avg(letzte `promote_after_n` Outcomes) ≥ `promote_score_threshold` → eine Stufe weiter
- **Demote** (priorisiert): avg(letzte `demote_after_n` Outcomes) < `demote_score_threshold` → eine Stufe zurück
- **Frischstart** nach Transition: `recent_outcomes` werden geleert, verhindert Oszillation

Defaults: `promote_after_n=30`, `score≥0.9`; `demote_after_n=5`, `score<0.7`. Settings admin-UI-fähig.

### AUTONOMOUS-Revision-Loop

In Stage `(e)` führt das System die Aktion aus, validiert, und bei DoD-Verfehlung läuft eine **Lesson-Feedback-Schleife**:

1. Record Lesson (Provenance: `author="orchestrator", source="autonomous_revision"`)
2. DoD re-derivieren (LessonsSource pickt neue Lesson auf)
3. `act()` nochmal
4. Validate
5. Loop bis success oder `max_revision_attempts` erreicht

Der Loop ist eine **menschen-gated Reflektion** — die KI versucht, aber die Plan-Gate-Schicht und Stage-Disziplin verhindern, dass der Loop das System destabilisiert.

Detail: [`LIFECYCLE.de.md`](LIFECYCLE.de.md).

## 6. M5 + Observability: Lesson-Feedback geschlossen

DoD-Erfüllung speist sich nicht nur aus statischen Frontmatter-Kriterien — Lessons aus `(c)/(d)/(e)`-Outcomes fließen via `LessonsSource` zurück in zukünftige `derive()`-Aufrufe:

```
User-Korrektur ──► LessonsAggregator.record_lesson()
                                 │
                                 ▼
                          LessonsStore (file-backed YAML)
                                 │
                                 ▼
                   LessonsSource.contribute()  (in next derive())
                                 │
                                 ▼
                   neue Criterion in DoD
```

Match-Mechanismus: `Lesson.context_pattern` ist ein dict. Eine Lesson matcht den aktuellen Kontext, wenn alle Pattern-Keys/Werte im Kontext vorhanden sind. Empty pattern → matches alles.

LessonsSource hat eigenen `max_confidence_delta`-Cap, um zu verhindern, dass eine Lessons-Flut den early-stop dominiert.

### Konkretes Loop-Beispiel — Verfehlung wird zu Vor-Wissen

```yaml
# Aktion N: extract_floor_plan auf einer Basement-Entity
# DoD aus EntityFrontmatterSource: rooms_count "3..15", parking_as_single_room True
# Effektor returnt: rooms_count=27 (alle <1.5m²)
# Validation: score=0.30, unsatisfied=[rooms_count, parking_as_single_room]
# AUTONOMOUS-Revision: max_attempts erschöpft, revision_pending=True

# Lesson auto-aufgezeichnet (Phase 5.0):
lesson:
  id: <uuid>
  kind: extract_floor_plan
  observation: |
    AUTONOMOUS revision attempt 2: validation failed on
    2 criteria (rooms_count, parking_as_single_room)
  context_pattern: {}  # generisch, gilt überall (Phase-4-Default)
  provenance:
    author: orchestrator
    source: autonomous_revision
```

```yaml
# Aktion N+1: extract_floor_plan auf nächster Basement-Entity
# Engine.derive():
#   1. EntityFrontmatterSource liefert rooms_count "3..15"
#   2. LessonsSource findet die Lesson aus Aktion N und emittiert
#      sie als Hint in die DoD
#   3. UC-Source leer (Definition-Confidence ausreichend)
# DoD enthält jetzt zusätzlich den Hint aus dem Verfehlungs-Loop
```

Damit lernt das System nicht nur „wann es richtig lag", sondern **wie seine eigenen Schwächen aussehen** — und bringt das in zukünftige DoDs ein. Das ist die zentrale Verkopplung zwischen Beobachtung (④) und Gedächtnis (②).

**Phase-4-Stand**: Lesson hat `criteria_hint=[]` (kein konkreter Pattern-Adjustment). Phase-6+-Erweiterung würde Lessons mit `proposed_dod_adjustment.add_criterion: {...}` produzieren — eine Distillation aus `validation.unsatisfied` zu konkreten Pattern-Empfehlungen. Heute ist die Lesson nur Marker; die DoD muss noch manuell oder durch externe Pattern-Distillation angepasst werden.

### Trace + Provenance + Events

Jeder `orchestrator.execute()`-Aufruf erzeugt einen **Trace** (`organism.observability.Trace`) mit allen relevanten Daten:
- `kind`, `request_summary`, `context`, `stage`, `status`
- `dod` (vollständig embedded)
- `validation` (mit score, all_satisfied, unsatisfied)
- `transition_to` (falls Stage-Übergang)
- `revision_pending` / `revision_attempts`
- `provenance` (author, timestamp)

Traces sind in `traces/{trace_id}.yaml` persistiert — file-first, grep-bar, OTel-konvertierbar.

**OTel-GenAI Mapping**: `trace_to_otel_span(trace) → dict` produziert OTel-Semantic-Conventions-konformes JSON mit `gen_ai.*` und `organism.*`-Attributen. Struktur-only, keine Runtime-Dependency auf `opentelemetry-api/sdk` — externe Exporter (Langfuse, Jaeger, OpenTelemetry-Collector) konsumieren das Output.

**EventBus** propagiert vier Event-Typen für Cross-Component-Logik:
- `plan_proposed` (Orchestrator nach `plan_gate.propose`)
- `lifecycle_transition` (Orchestrator nach `lifecycle.record_outcome`)
- `trace_recorded` (Orchestrator nach Trace-Write)
- `lesson_recorded` (LessonsAggregator nach `record_lesson`)

Detail: [`OBSERVABILITY.de.md`](OBSERVABILITY.de.md).

## 7. Cross-Domain-Validation

Drei parallel implementierte Demo-Domänen beweisen die Domänen-Unabhängigkeit der Pipeline-Logik:

| Demo | Domain | Action-Kind | Effektor | Entities |
|---|---|---|---|---|
| `architect_lite` | Architekturbüro | `extract_floor_plan` | `FloorPlanExtractor` | 3 Floor Plans |
| `tax_lite` | Steuerberatung | `validate_tax_return` | `TaxReturnValidator` | 3 Mandanten |
| `cfo_lite` | CFO-Office | `run_close_step` | `QuarterlyCloseRunner` | 3 Reporting-Perioden |

Alle drei Demos durchlaufen einen identischen 4-Schritt-Walk:

1. Stage PROPOSED — voller propose → approve → apply Flow
2. Stage CHECKED — 3 erfolgreiche Aktionen → Promotion zu ROUTINE
3. Stage AUTONOMOUS — failing Effector → Revision-Loop → `revision_pending=True`
4. Manuelle HITL-Lesson via `aggregator.record_lesson()`

### Pipeline-Counts identisch

| Metrik | architect_lite | tax_lite | cfo_lite |
|---|---|---|---|
| Aktionen ausgeführt | 6 | 6 | 6 |
| Plans vorgeschlagen | 1 | 1 | 1 |
| Plans applied | 1 | 1 | 1 |
| Traces aufgezeichnet | 6 | 6 | 6 |
| Lessons aufgezeichnet | 3 | 3 | 3 |
| Events captured | 11 | 11 | 11 |
| Transitions beobachtet | 1 | 1 | 1 |
| Final stage | autonomous | autonomous | autonomous |

→ Automatisiert geprüft via `tests/examples/test_cross_demo.py`. Wenn dieser Test bricht, ist die Genericity gefährdet.

### Code-Verhältnis

- **Domain-Code** (`examples/<domain>/`): ~300 Zeilen über 3 Demos
- **Pipeline-Code** (`src/organism/`): ~3000 Zeilen

Eine vierte Domain wäre wieder ~300 Zeilen — Genericity hat ein konkretes Maß.

Detail: [`DEMOS.de.md`](DEMOS.de.md).

## 8. Status & Offene Fragen

### Reference-Implementation-Stand (2026-05-10)

- **Phase 0**: Skelett-Init
- **Phase 1**: Memory + Effector-Vertrag (Phase 1.1-1.4)
- **Phase 2**: DoD-Engine + Validator (Phase 2.1-2.5, Kernstück)
- **Phase 3**: Settings + Plan-Gate + Lifecycle + Orchestrator (Phase 3.0-3.3)
- **Phase 4**: Provenance + Trace + Lessons + Observability (Phase 4.0-4.3)
- **Phase 5**: AUTONOMOUS-Revision + Events + 3 Demos (Phase 5.0-5.5)
- **Phase 6**: Doku-Konsolidierung (in Arbeit)

503 Tests grün, 35 Commits, 4 detail-Whitepaper (STAR/LIFECYCLE/OBSERVABILITY/DEMOS), 11 entkernte ARCHITEKTUR-Chapter.

### Offene Fragen für Implementations-Vertiefung

#### DoD-Engine

- **Threshold-Tuning**: globaler Default `0.8`. Effector-spezifisch? Lernen über Action-Verlauf?
- **Source-Disable**: aktuell nur via Subset-Filter im Konstruktor. Reicht das oder braucht es ein Capabilities-Modell?
- **Confidence-Aggregation**: aktuell sum-capped. Alternative: gewichteter Mittelwert per Source-Reliability?
- **DoD-Caching**: pro `(request_signature, context_signature)` cachen?
- **Comparator-Erweiterung**: aktuell Range/Threshold/Equality/Callable. Bedarf für Set-Membership, Regex?
- **DoD-Evolution über Versionen**: wenn der Steckbrief sich ändert, ändert sich die DoD. Wie wird verglichen „Effektor ist bei `fulfillment_score=0.85`" über DoD-Versionen hinweg? Brauchen Versions-Paar-Tracking, ist nicht-trivial.
- **Cross-Tool-DoD**: was ist die DoD einer Pipeline aus 3 Effektoren? Aggregation der einzelnen DoDs, oder eigene Pipeline-DoD? Hängt mit M4 zusammen.
- **DoD-Konflikte zwischen Quellen**: Steckbrief sagt `rooms_count=25..35`, RelatedEntities sagt `30..40`. Was gewinnt? Heute gewinnt Hierarchie (Schritt 1 vor Schritt 3). Ist das immer richtig?

#### DoD-Engine: Qualitative Kriterien — `evaluator`-Schalter (Phase 7.1, implementiert)

`Criterion.evaluator` wählt den Bewertungspfad pro Kriterium. Drei Modi decken das praktische Spektrum:

```
rule         deterministisch (Range / Threshold / Equality / Callable)
self_check   Effektor self-attests im Result-Dict
llm_judge    Konsumenten-Callable bewertet
```

`llm_judge` ist der teuerste Modus, darum nur dort einsetzen wo `rule` oder `self_check` nicht reichen. Faustregel: ein qualitatives Kriterium pro DoD ist Standard, drei sind viel. Konsumenten injizieren die Bewertungs-Callables über `EvaluationContext(llm_judge=..., self_check=...)`. Das Skelett selbst hat keine LLM-Abhängigkeit.

Ohne Callable liefert `llm_judge` `(False, "no llm_judge callable configured")` — kein Silent-Pass.

#### DoD-Engine: Lesson-Distillation (Phase 7.2, implementiert)

`_record_revision_lesson` füllt `criteria_hint` jetzt aus `validation.unsatisfied` (statt der früheren leeren Liste). Pro Kriterium gilt:

```yaml
criteria_hint:
  - name: <verfehltes Kriterium>
    expected: <ursprünglicher Erwartungswert>
    weight: <ursprüngliches weight * revision_lesson_weight_factor>   # Default 0.5
    source: dod_failure
    evaluator: <preserved>
    revision_strategy: <preserved>
```

`LessonsSource` zieht die Kriterien beim nächsten `engine.derive()` zurück in die DoD — der Loop schließt sich. `OrchestratorSettings.lesson_context_keys` steuert welche ctx-Keys ins `context_pattern` der Lesson wandern; Default ist eine leere Liste, d.h. die Lesson wird kontextfrei gegen den `kind` gematcht. Konsumenten überschreiben mit z.B. `["domain", "subtype"]` für engere Match-Bedingungen.

#### Lifecycle

- **Per-kind Transition-Policy**: aktuell global. Heikle Schreibvorgänge brauchen vielleicht konservativere Schwellen.
- **Plan-Expiration**: Time-based Auto-Expiry?
- **Score-Aggregation**: Median statt Mean (robuster gegen Outlier)?
- **Multi-Stakeholder-Approve**: Vier-Augen-Prinzip als Erweiterung?

#### Lifecycle: Granulare Revisions-Modi pro Kriterium (Phase 7.3, implementiert)

`Criterion.revision_strategy` wählt pro Kriterium die Reaktion auf Verfehlung in AUTONOMOUS:

```
retry_alt_params      iteratives Retry bis autonomous_max_revision_attempts
                      (Default — entspricht dem bisherigen Verhalten)
escalate_to_human     Lesson + Plan-Gate-Eintrag mit failed_criteria,
                      ActionStatus.PROPOSED, kein weiterer Retry
rollback_and_log      Lesson + effector.rollback(action_descriptor, result)
                      (optional via hasattr — Effector-Protocol bleibt unverändert),
                      ActionStatus.DENIED
```

Bei mehreren verfehlten Kriterien gewinnt die strengste Strategie: `rollback > escalate > retry`. Per-Action-Default via `OrchestratorSettings.default_revision_strategy`.

#### Operative Defaults (Phase 7.4, implementiert)

```
on_definition_unclear   ask | abort | proceed_with_warning
on_fulfillment_failed   warn | retry | abort
fulfillment_score_pass  0.0..1.0 (Default 1.0 = strict; M5-Empfehlung 0.8)
```

Mit `fulfillment_score_pass=0.8` wird eine Aktion mit `validation.score >= 0.8` als erfüllt gewertet — auch wenn schwache Kriterien fallen. `on_fulfillment_failed` greift in CHECKED/ROUTINE und in `apply_approved_plan` (AUTONOMOUS nutzt die Revisions-Strategien). Surface über `ValidationResult.is_fulfilled(threshold)`.

#### Observability

- **Trace-Retention**: heute unlimited. Time-based Cleanup?
- **Trace-Indexing**: bei vielen Traces wird `list()` linear-scan teuer.
- **Lessons-Lift-Tracking**: alt-vs-neu Score-Vergleich, Promotion zu DoD-Default.
- **EventBus-Persistierung**: heute in-memory.
- **OTel-Span-Children**: heute flat. Hierarchische Spans?
- **Provenance-Unifikation**: Plan/DoD/Lifecycle haben heute partielle Provenance — eine spätere Phase könnte das vereinheitlichen.

### Offene Fragen für externe Konsumenten (Phase 7+)

- **Plan-Gate-UI**: Web-Cockpit mit Notification-Channel
- **Auto-ToolRegistry-Registrierung**: Effectors registrieren via Decorator
- **Echter HTTP-Push** zu Langfuse/Jaeger via OTel-Exporter
- **Self-Improvement-Worker** in echter Sandbox (E2B / Firecracker / Container)
- **InsightService** für Cross-Effector-Anfragen
- **Karpathy-Loop** für autonome Few-Shot-Generation

## 9. References

### Bestehende Patterns die das System adoptiert

- [Anthropic Agent Skills (December 2025)](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills) — YAML-Frontmatter + Markdown-Body als Standard-Konvention
- [OpenTelemetry GenAI Semantic Conventions](https://opentelemetry.io/docs/specs/semconv/gen-ai/) — Provenance + Span-Attribute
- [Levels of Autonomy for AI Agents (Knight Institute, arXiv 2506.12469)](https://arxiv.org/abs/2506.12469) — Lifecycle-Stage-Vokabular (per User-Rolle, das Skelett ist per Aktion granularer)
- [LangGraph `interrupt_on`](https://docs.langchain.com/oss/python/langchain/human-in-the-loop) — Human-in-the-Loop als Schicht
- [Reflexion (Shinn et al., 2023, arXiv 2303.11366)](https://arxiv.org/pdf/2303.11366) — Self-Critique-Pattern (verwandt zum `self_check` / `llm_judge`-Schalter und zur Verfehlungs-Lesson-Distillation in Phase 7.1/7.2)
- [Letta File-Memory Benchmark (2026)](https://www.letta.com/blog/benchmarking-ai-agent-memory) — empirische Validierung von File-First-Memory

### Neuartige Beiträge des Skeletts

- **6-Quellen-DoD-Recherche-Hierarchie** mit globaler Priority-Reihenfolge — kein veröffentlichtes Pattern hat das in dieser Form (Scrum.org „DoD for AI Agents" als nächster Treffer mit ~40% Match: statisches DoD-Set, keine Recherche-Hierarchie).
- **Aktions-Lebenszyklus per Action-Kind** mit avg-Score-getriebenen Stage-Transitions, Sliding-Window, Frischstart nach Transition. Knight 2506.12469 nennt das explizit „future work".
- **AUTONOMOUS-Revision-Loop** mit Lesson-Feedback in einer geschlossenen Schleife.
- **Cross-Domain-Verifikation als executable spec** (`tests/examples/test_cross_demo.py`).

### Reference-Implementation

Open-Source-Skelett: https://github.com/organism-core/organism-core

```bash
python -m examples.architect_lite    # Architekturbüro-Demo
python -m examples.tax_lite          # Steuerberatungs-Demo
python -m examples.cfo_lite          # CFO-Office-Demo
pytest tests/                         # 503 Tests grün
```

---

**Schlussbild**

Was unten konstant bleibt, ermöglicht oben das Variieren. Domäne ist austauschbar, die fünf Bauteile und fünf Patterns sind konstant, der Mensch bleibt im Mittelpunkt. M5 ist das verbindende Glied, das aus losen Bauteilen einen Organismus macht — ein System, das nicht nur reagiert, sondern bewertet was es tut.
