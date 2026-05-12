*[🇬🇧 English version](STAR.md)*

# STAR — Definition-of-Done-Recherche-Engine

> Konzept-Skizze als Whitepaper-Vorbereitung für Phase 6.
> Stand: 2026-05-09, nach Phase 2.4.

## Motivation

In jedem Multi-Tool-System mit autonomen Akteuren entsteht eine implizite Lücke: **was ist eine „korrekte" Aktion?**

Klassische Erfolgs-Maßstäbe greifen nicht weit genug:
- Tests laufen → prüft Code-Korrektheit, nicht Aktions-Korrektheit
- Mensch korrigiert nachträglich → reaktiv, langsame Lernkurve
- Konfidenzwert vom LLM → selbstreferentiell, nicht kalibriert

Der **DoD-Pattern** (Definition of Done) schließt diese Lücke durch eine zweiteilige Regel:

> Vor jeder Aktion mit Außenwirkung **recherchiert** das System die Definition of Done. Findet es keine ausreichend klare DoD, fragt es den User mit gezielten Rückfragen — bevor es handelt. **Nach** der Aktion misst es die Erfüllung der DoD und schreibt das Ergebnis zurück ins Gedächtnis.

Der zweite Satz ist die wichtigere Hälfte. DoD ist nicht nur Vor-Recherche, sondern auch Nach-Bewertung. Erst durch das geschlossene Loop wird das System **bewertend** statt nur reaktiv — und durch das Aufschreiben der Verfehlungs-Lessons **selbst-korrigierend**.

Die DoD wird nicht erfunden, sondern recherchiert aus mehreren Quellen, in fester Reihenfolge von _spezifisch+konkret_ über _erprobt_ und _normativ_ zu _fragend_.

### Zwei Konfidenz-Größen — bitte nicht verwechseln

M5 unterscheidet **zwei orthogonale** Größen, die beide mit „Konfidenz/Score" benannt werden:

- **Definition-Confidence** (`DoD.confidence`, vor `act()`) — wie sicher ist das System, dass die DoD selbst gut formuliert ist? Steigt mit jeder Source-Contribution; sum-capped `[0,1]`. Steuert Early-Stop.
- **Fulfillment-Score** (`ValidationResult.score`, nach `act()`) — wie gut wurde die DoD erfüllt? Gewichtete Quote der erfüllten Kriterien. Steuert Lifecycle-Stage-Transitions.

Eine **gut definierte DoD mit hoher Definition-Confidence** kann nach der Aktion einen **niedrigen Fulfillment-Score** haben — das ist der Normal-Fall einer klar erkannten Verfehlung.

## Der Stern — Hub-and-Spoke

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
                  (6) UserClarification
                       (terminal)
```

Der Name „STAR" ist eine Form-Metapher — kein spezifischer Algorithmus aus der Literatur. Die radiale Struktur ist die zentrale Eigenschaft: jede Quelle ist gleichberechtigt _als Beitrag_, aber nicht gleichberechtigt _in der Reihenfolge_. Engine evaluiert in Priority-Reihenfolge `1→6` und stoppt früh, sobald DoD klar ist.

## Die sechs Quellen — Hierarchie

| # | Quelle | Was sie beiträgt | Phase 2 |
|---|---|---|---|
| 1 | EntityFrontmatterSource | Deklarierte DoD im Frontmatter der referenzierten Entity | voll |
| 2 | LessonsSource | Was wurde früher als „fertig" akzeptiert (Tool-Erfahrung) | Stub (Phase 4) |
| 3 | RelatedEntitiesSource | Cross-Reference: ähnliche Entities mit DoD-Hinweisen | Stub (Phase 5) |
| 4 | VectorSearchSource | Semantische Suche in Wissensbasis (Normen, Standards) | Stub (Phase 4) |
| 5 | DomainPatternSource | Domain-Standards und Master-Patterns | Stub (Phase 4) |
| 6 | UserClarificationSource | Terminale Rückfrage wenn 1-5 nicht reichen | voll |

Die Reihenfolge ist domänen-unabhängig begründet:
- **Spezifisch+konkret zuerst** (Entity > Related > Vector > Pattern): wer eine Antwort in der konkreten Entity findet, fragt nicht beim Vector-Store.
- **Erprobtes vor Normativem** (Lessons > Vector): Tool-eigene Lessons schlagen normative Texte, weil sie auf realen Praxisfällen basieren.
- **Normatives vor Fragendem** (1-5 > User): Normen schlagen User-Frage, weil der User seine Zeit nicht für Bekanntes verbrennen will.

Wer die Reihenfolge umkehrt, fragt den User Sachen die schon im Frontmatter stehen — das verbrennt User-Vertrauen.

Source-Reihenfolge ist **global fix**. Effectors wählen ein Subset, aber reordnen nicht.

## Architektur

```
┌─────────────────┐
│   Effector      │   (5-Kontakt-Adapter)
└────────┬────────┘
         │ define_done(request, ctx)
         ▼
┌─────────────────┐                   ┌──────────────────┐
│   DoDEngine     │ ──── call ─────► │  Source 1, 2, ... │
│   .derive()     │ ◄── contribute ── │                  │
│  (merge,        │                   └──────────────────┘
│   early-stop)   │
└────────┬────────┘
         │
         ▼
       DoD ─────────► act(request) ──────────► result
         │                                          │
         │                                          │
         └─────────► DoDValidator ◄─────────────────┘
                     .validate(dod, result)
                          ▼
                   ValidationResult
                   (score, all_satisfied, unsatisfied)
```

Engine + Validator sind ein Paar:
- **Engine** definiert: was soll erfüllt sein?
- **Validator** prüft: was wurde erfüllt?

Die Lücke zwischen beiden ist die ehrliche Erfolgs-Metrik.

### Datentypen (typed dataclasses)

```
Criterion           name, expected, weight, source
SourceContribution  source_name, criteria, confidence_delta,
                    clarifications, evidence
DoD                 criteria, clarification_needed, confidence,
                    evidence_sources, _provenance
                    .is_satisfied_for_act() :: bool

CriterionResult     name, satisfied, weight, expected, actual, reason
ValidationResult    criterion_results, score
                    .all_satisfied :: bool
                    .unsatisfied   :: list
```

Alle haben `.to_dict()` für Logging und spätere OTel-GenAI-Konvertierung (Phase 4).

### DoDSource Protocol

```python
class DoDSource(Protocol):
    name: str
    def contribute(request, context, current) -> SourceContribution: ...
```

Strukturelles Subtyping (`runtime_checkable`) — kein Erbzwang, nur Methodensignatur. Eine Klasse mit den richtigen Attributen ist eine `DoDSource`, ohne explizit zu erben.

## Engine-Algorithmus

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
- _Criteria_: angefügt, mit `source` per `dataclasses.replace` gestempelt (kein Mutieren des Source-Internal-State)
- _Confidence_: sum-capped auf `[0, 1]`
- _Clarifications_: angefügt, order-preserving, keine Dedup
- _Provenance_: `source_name → list[criterion_name]`. Quellen die nur Evidence beitragen (ohne Kriterien) werden mit leerer Liste vermerkt; silent Quellen (gar nichts) erscheinen nicht.

**Early-Stop-Bedingung** ist konjunktiv:
- `confidence >= threshold` allein reicht NICHT — wenn Klärungen offen, weiter
- `clarification_needed empty` allein reicht NICHT — wenn Confidence niedrig, weiter

Andernfalls können nachfolgende Quellen die Klärung füllen oder die Confidence erhöhen. Default-Threshold: `0.8`, per Effector überschreibbar.

## Comparator-Semantik (Validator)

Hybrid-Strategie zur Unterstützung beider DoD-Definitionswege (Frontmatter-deklariert vs in-code):

| Form | Beispiel | Wann | Bedeutung |
|---|---|---|---|
| `callable` | `lambda v: v > 0` | in-code DoDs | invoked, `bool()` gecastet |
| `"lo..hi"` | `"25..35"` | YAML/Frontmatter | inklusiver numerischer Range |
| `">=N"` etc | `">=90%"`, `"<5"` | YAML/Frontmatter | Schwellwert (`>=`, `<=`, `>`, `<`), optional `%`-Suffix |
| anything | `True`, `42`, `"approved"`, `[1, 2]` | beide Wege | Equality (`==`) |

**Konventionen**:
- `%`-Suffix wird beim Parsing auf beiden Seiten gestrippt — User verantwortlich für konsistente Skala (z.B. beide Seiten `0..100` oder beide `0..1`).
- Bool wird im numerischen Kontext explizit abgewiesen (sonst würde `True == 1` Range-Tests verfälschen — Python bool ist int-Subklasse). Boolean-Equality (expected=True, actual=True) funktioniert weiterhin via Equality-Pfad.
- Callable-Exceptions werden gefangen, Kriterium gilt als unsatisfied mit Reason-Text. Andere Kriterien laufen unbeeinträchtigt weiter.
- Missing key vs explicit None ist unterschieden (reason vs equality-check).
- String-Actuals werden per `float()` coerced (mit `%`-Strip).

**Score** = `sum(weight if satisfied) / sum(all weights)`. Total-Weight=0 liefert `0.0` (keine Division durch 0). Leeres DoD: `score=0`, `all_satisfied=True` (vacuously).

## Lifecycle-Bezug

Die Aktions-Lebenszyklus-Stufen werden **erst durch DoD maschinen-bewertbar**:

| Stufe | Wer prüft DoD | Konsequenz bei Verfehlung |
|---|---|---|
| (a) manuell | Mensch tut, kein DoD nötig | — |
| (b) vorgeschlagen | System schlägt vor + zeigt DoD; Mensch bestätigt | Plan-Gate-Eintrag enthält DoD |
| (c) geprüft | System tut + checkt selbst gegen DoD; Mensch validiert | Bei DoD-Verfehlung: User-Hinweis statt stiller Fehler |
| (d) routiniert | System tut + DoD-Check automatisch; Mensch stichprobenhaft | Drift in DoD-Erfüllungsrate triggert Rückfall nach (c) |
| (e) eigenständig | System tut + DoD-Check + Revision wenn DoD verfehlt | Mensch nur bei Anomalie (DoD-Erfüllung < Schwelle) |

**DoD-Erfüllungsrate über N Aktionen** entscheidet, ob eine Aktion in (a)→(e) wandert oder zurück. Phase 3 (Plan-Gate + Lifecycle) konsumiert die Validator-Outputs als Stage-Transition-Signal.

## Beispielszenarien (Cross-Domain)

Die drei Demo-Domains zeigen identische Engine-Logik bei unterschiedlichem Inhalt — der Trenn-Test in Aktion. Alle drei nutzen die gleiche Konvention `frontmatter.dod.criteria`.

### architect_lite

```yaml
# examples/architect_lite/entities/villa-alpha/basement/_entity_profile.md
---
type: residential
floor: basement
dod:
  criteria:
    - name: rooms_count
      expected: "3..15"
      weight: 1.0
    - name: rooms_with_doors
      expected: ">=70%"
      weight: 0.8
    - name: parking_as_single_room
      expected: true
      weight: 0.5
---
```

### tax_lite

```yaml
# examples/tax_lite/entities/client-042/2024/_entity_profile.md
---
type: income_tax_return
fiscal_year: 2024
dod:
  criteria:
    - name: all_income_recorded
      expected: true
      weight: 1.0
    - name: deductions_plausible
      expected: ">=0"
      weight: 0.7
    - name: tax_class_in_valid_range
      expected: "1..6"
      weight: 1.0
---
```

### cfo_lite

```yaml
# examples/cfo_lite/entities/2024-Q3/_entity_profile.md
---
type: quarterly_close
fiscal_year: 2024
quarter: 3
dod:
  criteria:
    - name: cost_centers_closed
      expected: true
      weight: 1.0
    - name: provisions_updated
      expected: true
      weight: 0.9
    - name: budget_variance
      expected: "-0.05..0.05"
      weight: 0.5
---
```

Alle drei Domains: identische Engine, identischer Validator, gleiche Konvention. Was nicht in allen drei läuft, ist zu domänen-spezifisch und gehört nicht ins Skelett.

## Status & Offene Fragen

### Phase 2 Liefer-Stand (Stand 2026-05-09)

- DoDEngine vollständig (Phase 2.1)
- EntityFrontmatterSource voll (Phase 2.2)
- 4 Stub-Sources mit stabiler API (Phase 2.3)
- DoDValidator mit hybridem Comparator (Phase 2.4)
- 144 Tests grün

### Phase 4+ ergänzt

- LessonsSource: Anbindung an Lesson-Aggregator (Phase 4)
- VectorSearchSource: Anbindung an Vector-Store-Client (Phase 4)
- DomainPatternSource: Anbindung an Pattern-Registry (Phase 4)
- RelatedEntitiesSource: Similarity-Funktion über `EntityStore` (Phase 5)
- Provenance-Schema in OTel-GenAI-Konvertierung (Phase 4)

### Wann DoD-Recherche verzichtbar ist

Schärfere Heuristik als „Lese vs. Schreib" (eine Vector-Suche ist Lesen, hat aber Erfolgs-Kriterien):

- **Verzichtbar** bei **deterministischen** Operationen (SQL-Lookup, Datei-Read, exakter Schema-Match)
- **Verzichtbar** in Stage `(a) MANUAL`
- **Pflicht** bei **probabilistischen** Operationen, auch lesenden (Vector-Search-Ranking, Klassifikation, OCR, KI-basierte Extraktion)
- **Pflicht** ab Stage `(b) PROPOSED`
- **Pflicht** bei jeder Schreibaktion in den Wahrheits-Speicher

### Offene Fragen für Phase 6 (Whitepaper-Konsolidierung)

- **Threshold-Tuning**: globaler Default `0.8`, aber wann ist das richtig? Effector-spezifisch? Lernen über Action-Verlauf?
- **Source-Disable per Effector**: aktuell nur via Subset-Filter beim Konstruktor. Reicht das oder braucht es ein Capabilities-Modell?
- **Confidence-Aggregation**: aktuell sum-capped. Alternative: gewichteter Mittelwert per Source-Reliability?
- **DoD-Caching**: pro `(request_signature, context_signature)` cachen? Phase 4 spielt das durch.
- **Sprache**: dieses Dokument ist deutsch. Public-Schaltung in Phase 6 erfordert englische Version oder Bilingual.
- **Comparator-Erweiterung**: aktuell Range, Threshold, Equality, Callable. Bedarf für Set-Membership (`expected = ["a", "b"]` als „in"), Regex (`expected = "^foo.*"`)?
- **Weighted vs strict Score**: aktuell gewichtete Quote. Alternative: strict (alle satisfied = `1.0`, sonst `0`)?
- **Negative Confidence**: heute floor `0.0`, gegen Source-Mistrust geschützt. Use Case für negative Beiträge (Source widerspricht aktiv)?
- **DoD-Evolution über Steckbrief-Versionen**: wenn das Frontmatter sich ändert, ändert sich die DoD. Wie wird `fulfillment_score` über DoD-Versionen verglichen?
- **Cross-Tool-DoD**: Pipeline aus 3 Effektoren — Aggregation der einzelnen DoDs oder eigene Pipeline-DoD?
- **DoD-Konflikte zwischen Quellen**: Steckbrief sagt `25..35`, RelatedEntities sagt `30..40`. Heute gewinnt Hierarchie (Schritt 1 vor 3). Immer richtig?

### Qualitative Kriterien — `evaluator`-Schalter (Phase 7.1, implementiert)

`Criterion.evaluator` wählt den Bewertungspfad:

```
rule         deterministisch (Range / Threshold / Equality / Callable)
self_check   Effektor self-attests im Result-Dict
llm_judge    Konsumenten-Callable bewertet (Skelett bringt keine LLM-Lib mit)
```

`llm_judge` ist der teuerste Modus, darum nur dort einsetzen wo `rule` oder `self_check` nicht reichen. Faustregel: ein qualitatives Kriterium pro DoD ist Standard, drei sind viel.

Konsumenten injizieren die Bewertungs-Callables über `EvaluationContext(llm_judge=..., self_check=...)`. Ohne Callable liefert `llm_judge` `(False, "no llm_judge callable configured")` — kein Silent-Pass.

### Granulare Revisions-Modi pro Kriterium (Phase 7.3, implementiert)

`Criterion.revision_strategy` wählt pro Kriterium die Reaktion auf Verfehlung in AUTONOMOUS:

```
retry_alt_params      heutiges Verhalten (Default) — iteratives Retry bis
                      autonomous_max_revision_attempts
escalate_to_human     Lesson + Plan-Gate-Eintrag mit failed_criteria —
                      ActionStatus.PROPOSED, kein Retry
rollback_and_log      Lesson + effector.rollback(descriptor, result) (optional
                      via hasattr) — ActionStatus.DENIED
```

Bei mehreren verfehlten Kriterien gewinnt die strengste Strategie: `rollback > escalate > retry`. Default-Strategie via `OrchestratorSettings.default_revision_strategy`.

### Lesson-Distillation aus DoD-Verfehlung (Phase 7.2, implementiert)

`_record_revision_lesson` füllt `criteria_hint` aus `validation.unsatisfied`. Gewicht pro Kriterium wird auf das `revision_lesson_weight_factor`-fache (Default 0.5) reduziert; `source` wird auf `"dod_failure"` gesetzt; `evaluator` und `revision_strategy` bleiben erhalten. `LessonsSource` zieht die Kriterien beim nächsten `engine.derive()` zurück in die DoD — der Loop schließt sich.

`OrchestratorSettings.lesson_context_keys` steuert welche Kontext-Keys ins `context_pattern` der Lesson wandern (Default: leer = kontextfreier Match auf `kind`).

### Operative Defaults (Phase 7.4, implementiert)

```
on_definition_unclear   ask | abort | proceed_with_warning   (Default ask)
on_fulfillment_failed   warn | retry | abort                 (Default warn)
fulfillment_score_pass  0.0..1.0                             (Default 1.0)
```

Mit `fulfillment_score_pass=0.8` (M5-Patch-Empfehlung) wird eine Aktion mit `validation.score >= 0.8` als erfüllt gewertet — auch wenn schwache Kriterien fallen. Mit Default `1.0` ist die Semantik strict (entspricht `all_satisfied`). `on_fulfillment_failed` greift in CHECKED/ROUTINE und in `apply_approved_plan`; AUTONOMOUS nutzt die Revisions-Strategien.
