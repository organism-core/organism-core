# 09 — Universelles Framework

> Was Kapitel 00–08 als konkretes System beschreiben, lässt sich auf
> ein generisches Skelett bringen. Dieses Skelett ist der Bauplan für
> jede vergleichbare Tool-Landschaft — Architekturbüro, Kanzlei,
> Krankenhaus, Steuerberater, Forschungsgruppe.

## Die fünf Bauteile

```
   ╭──────────────────────────────────────────────────────────────╮
   │                                                              │
   │   ① EFFEKTOREN  ───→ ② GEDÄCHTNIS ←─── ③ NERVENSYSTEM        │
   │   (Tools)            (Daten,             (Code,              │
   │                       hart verdrahtet)    fluide)            │
   │       ▲                  ▲                  ▲                │
   │       │                  │                  │                │
   │       └──────────────────┼──────────────────┘                │
   │                          │                                   │
   │                  ④ BEOBACHTUNG                               │
   │                  (Tracking,                                  │
   │                   speist zurück)                             │
   │                                                              │
   │  ⑤ AKTIONS-LEBENSZYKLUS  manuell → vorgeschlagen →           │
   │                          geprüft → routiniert → eigenständig │
   │                                                              │
   ╰──────────────────────────────────────────────────────────────╯
```

### ① Effektoren — was greift in die Welt
Halbselbständige Werkzeuge mit klarer Domäne. Jedes hat:
- eine **Aufgabe** (was greift es an)
- **Sensoren** (woher liest es)
- **Effektoren** (was schreibt es)
- eine **Schnittstelle** (Capabilities, MCP, A2A)
- einen **Provenance-Output** (warum hat es das gesagt)

Effektoren sind **austauschbar**. Wer ein Tool ablöst, ändert
Capabilities, das System bleibt funktionsfähig.

### ② Gedächtnis — was bleibt
Daten sind **hart verdrahtet**. Sie haben:
- ein klares **Schema** (Felder, Konventionen)
- einen **Wahrheits-Speicher** (Dateisystem mit menschenlesbaren
  Formaten — niemals proprietäre DB als einzige Quelle)
- **Index-Schichten** für Suche (Vektordatenbank, Volltextindex)
- **Provenance** und **Version** auf jedem Eintrag (wer, wann, woher,
  wie sicher)

Gedächtnis ist **nicht austauschbar**. Wer das Schema ändert, bricht
alles. Darum gilt: erst dokumentieren, dann ändern.

Trennung Gedächtnis vs Nervensystem ist die wichtigste
Architektur-Entscheidung. **Daten leben länger als Code.** Wenn das
KI-System morgen weg ist, müssen die Daten weiter bedienbar sein.

### ③ Nervensystem — was koordiniert
Code-Schicht zwischen Effektoren und Gedächtnis. Sie:
- holt Kontext (Steckbrief-Lookup, Cache, Capability-Discovery)
- routet Aufrufe (Tool A → Tool B, Aggregation)
- gated Schreibaktionen (Plan-Gate, Approve-Cockpit)
- transportiert Events (Pub/Sub statt Import-Kopplung)

Nervensystem ist **fluide**. Code wird umgebaut, neue Services
kommen, alte werden ersetzt — ohne Daten anzufassen. Wenn das
Nervensystem brennt, das Gedächtnis bleibt.

### ④ Beobachtung — was lernt
Telemetrie-Schicht parallel zu allem. Erfasst:
- jeden Tool-Aufruf (was, wann, wieviel Tokens, wie lange)
- jede User-Aktion auf KI-Outputs (approve, reject, edit, ignore)
- jede Plan-Gate-Entscheidung (mit Latenz und Begründung)
- jede Lesson (was wurde wie aus was destilliert)

Beobachtung ist **rückwirkend**. Sie speist:
- ins **Gedächtnis** zurück (Lessons → Pattern-Bibliothek →
  Few-Shots beim nächsten Mal)
- ins **Nervensystem** zurück (Promotion-Vorschläge, Self-Improvement-
  Code-Patches, Capability-Lücken-Analyse)

Wer keine Beobachtung hat, hat ein System das altert. Wer sie hat
und nicht zurückspeist, hat ein Archiv. Erst der Rückkanal macht es
ein lernendes System.

### ⑤ Aktions-Lebenszyklus — wie Aktionen reifen
Jede automatisierbare Aktion durchläuft fünf Stufen, in dieser
Reihenfolge, ohne Sprung:

```
  manuell ──→ vorgeschlagen ──→ geprüft ──→ routiniert ──→ eigenständig
   (a)            (b)             (c)           (d)            (e)
```

- **(a) manuell** — Mensch tut es. KI sieht zu, sammelt Beispiele.
- **(b) vorgeschlagen** — KI schlägt vor. Mensch sagt ja/nein. Jeder
  Vorschlag ein Plan-Gate-Eintrag.
- **(c) geprüft** — KI tut es. Mensch validiert nachträglich (alles).
  Reject = Lesson, Approve = Trainingssignal.
- **(d) routiniert** — KI tut es. Mensch stichprobenhaft. System
  beobachtet Drift; bei Anstieg automatisch zurück zu (c).
- **(e) eigenständig** — KI tut es, beobachtet sich selbst, kann
  revidieren. Mensch nur noch bei Anomalien einbezogen.

**Pflicht**: keine Stufe überspringen. Wer (a) → (e) springt, baut
ein Black-Box-System ohne Vertrauensaufbau.

**Pflicht**: jede Aktion hat eine sichtbare Stufenangabe — der User
weiß zu jeder Zeit "wie selbständig ist das hier".

**Möglich**: Rückwärtsbewegung. Eine Aktion kann von (d) zurück nach
(c), wenn die Drift-Rate steigt. Das ist kein Versagen, das ist
gesundes Verhalten.

## Die zwei kreuzenden Achsen

### Achse 1: hart ↔ fluide

```
   hart verdrahtet ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ fluide
        │                                              │
        ▼                                              ▼
   ② Gedächtnis                                  ③ Nervensystem
   - Schema-Verträge                             - Service-Layer
   - Datei-Pfade                                 - Pipeline-Stufen
   - Provenance-Felder                           - Prompt-Texte
                                                 - Modell-Wahl
```

**Hart** ist alles wo Änderung Daten kosten würde.
**Fluide** ist alles wo Änderung nur Code kostet.

Wer fluide Sachen hart macht (Modell-Wahl in Datenbank speichern),
verliert Beweglichkeit. Wer harte Sachen fluide macht (Schema in
Code generiert), verliert Stabilität.

### Achse 2: synchron ↔ asynchron

```
   synchron (Reflex) ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ asynchron (Lernen)
        │                                                │
        ▼                                                ▼
   - Steckbrief-Lookup                              - Lesson-Aggregation
   - Capability-Discovery                           - Pattern-Promotion
   - User-Klick → Reaktion                          - Karpathy-Few-Shots
                                                    - Self-Improvement-Patch
```

Synchron darf nichts kosten — Millisekunden. Asynchron darf alles
kosten — Stunden, Tage. Wer asynchron in den synchronen Pfad legt
(LLM-Call beim Steckbrief-Lookup), zerstört das System für den User.

## Der Aktions-Adapter — was ein Werkzeug haben muss

Damit ein Effektor ins Framework passt, exposes er **fünf
Kontaktstellen**:

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│   ┌── pre_load(context) ──→  Kontext laden vor Aktion    │
│   │                          (M1 Prä-Lookup-Pattern)     │
│   │                                                      │
│   ├── define_done(input, ctx) → DoD herleiten            │
│   │                          (M5 DoD-Pattern, siehe unten)│
│   │                                                      │
│   ├── act(input) ───────→   Aktion ausführen             │
│   │                          (mit Stage-Marker a-e)      │
│   │                                                      │
│   ├── upstream(kind, payload) →  Meldung nach oben       │
│   │                          (M2 Upstream-Pattern:       │
│   │                          provenance/lesson/conflict) │
│   │                                                      │
│   └── gate(action) ─────→   User-Approval bei Bedarf     │
│                              (M3 User-Gate-Pattern)      │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

Mehr braucht ein Tool nicht. Wer diese fünf Stellen sauber
implementiert, kann angeschlossen werden — egal ob das Tool ein
Vision-Modell, ein Crawler, eine OCR-Pipeline oder eine Excel-
Auswertung ist.

## M5 — Definition-of-Done-Pattern

Bisher hatte das Framework eine implizite Lücke: der
Lebenszyklus (a)→(e) misst Reife in "Korrektur-Anteil über Zeit",
aber **was eine korrekte Aktion ist** war undefiniert. Der User
merkte Fehler beim Sichten, das System lernte daraus — aber langsam,
weil die Erfolgs-Kriterien nirgends explizit waren.

M5 schließt das. Die zweiteilige Regel:

> **Vor jeder Aktion mit Außenwirkung recherchiert das System die
> Definition of Done. Findet es keine ausreichend klare DoD, fragt
> es den User mit maximal drei gezielten Fragen — bevor es handelt.
> Nach der Aktion misst es die Erfüllung der DoD und schreibt das
> Ergebnis zurück ins Gedächtnis.**

Der zweite Satz ist die wichtigere Hälfte: DoD ist nicht nur
Vor-Recherche, sondern auch Nach-Bewertung. Die DoD-Engine liefert
zwei orthogonale Größen — `dod.confidence` (Definition-Confidence
vor `act()`) und `validation.score` (Fulfillment-Score nach `act()`).
Detail in [`docs/STAR.de.md`](../STAR.de.md) und
[`docs/M5_WHITEPAPER.de.md`](../M5_WHITEPAPER.de.md).

### DoD-Recherche-Hierarchie

Das System sucht in genau dieser Reihenfolge, hört auf wenn DoD
ausreichend klar ist:

1. **Projekt-Steckbrief** — projekt-spezifische Erwartungen
   (typ=klinik → 25-35 Räume, 1:50)
2. **Tool-eigene Lessons** — was wurde früher als "fertig" akzeptiert
   (lesson_aggregator, _ki_erfahrung)
3. **Cross-Reference (RelatedEntities)** — ähnliche frühere Aktionen
   (andere Entities für gleichen Typ)
4. **ChromaDB-Volltext** — Normen, Standards, Vorlagen
   (DIN 277 Raumprogramm, DIN 1356 Plansymbolik, ...)
5. **Master-Patterns** — Bauteil-/Domain-Standards
   (Tür 88×201 bei Patientenzimmer)
6. **User-Frage** — wenn 1-5 nicht reichen, gezielte Klärung
   (max 3 Fragen, knapp, mit Default-Vorschlag)

Diese Hierarchie ist nicht zufällig. Sie geht von **spezifisch+konkret**
(Steckbrief) über **erprobt** (Lessons) zu **normativ** (DIN) zu
**fragend**. Wer die Reihenfolge umkehrt, fragt den User Sachen die
schon im Steckbrief stehen — das nervt und verbrennt Vertrauen.

### DoD-Schema

`define_done(input, context)` liefert:
```python
{
  "criteria": [
    {"name": "rooms_count", "expected": "25..35", "weight": 1.0},
    {"name": "rooms_with_doors", "expected": ">=90%", "weight": 0.8},
    {"name": "wall_thickness_consistent", "expected": True, "weight": 0.5},
  ],
  "evidence_sources": ["self_check", "user_validation"],
  "clarification_needed": [],   # leer = DoD klar
  "confidence": 0.85,
  "_provenance": {              # P3-Pflicht auch hier
    "from_steckbrief": ["typ", "raum_anzahl_erwartet"],
    "from_lessons": ["L42_klinik_wandstaerke"],
    "from_norms": ["DIN_277"],
  }
}
```

Wenn `clarification_needed` nicht leer ist, läuft `act()` nicht.
Stattdessen wird die User-Frage gestellt und die Antwort als Lesson
gespeichert (für die nächste DoD-Recherche).

### Wie der Lebenszyklus dadurch operationalisiert wird

Erst mit DoD wird (a)→(e) **maschinen-bewertbar** statt subjektiv:

| Stufe | Wer prüft DoD | Konsequenz |
|---|---|---|
| (a) manuell | Mensch tut, kein DoD nötig | — |
| (b) vorgeschlagen | System schlägt vor + zeigt DoD; Mensch bestätigt | Plan-Gate-Eintrag enthält DoD |
| (c) geprüft | System tut + checkt selbst gegen DoD; Mensch validiert | Bei DoD-Verfehlung: User-Hinweis statt stiller Fehler |
| (d) routiniert | System tut + DoD-Check automatisch; Mensch stichprobenhaft | Drift in DoD-Erfüllungsrate triggert Rückfall nach (c) |
| (e) eigenständig | System tut + DoD-Check + Revision wenn DoD verfehlt | Mensch nur bei Anomalie (DoD-Erfüllung <Schwelle) |

Das ist die Brücke zwischen "abstrakte Lebenszyklus-Stufe" und
"konkret messbare Reife": **DoD-Erfüllungsrate über N Aktionen
entscheidet ob es weiter wandert oder zurück.**

### Beispiel — Plan-Extraktion mit M5

Aktion: „Floor-Plan einer Kellergeschoss-Entity extrahieren"

DoD-Recherche durch das System (`engine.derive(request, context)`):

1. **EntityFrontmatterSource**: Steckbrief der Entity → `type=residential, floor=basement` erwartet
2. **LessonsSource**: matching Lessons („Basement-Pläne haben oft Parkbereich als Einzelraum, flood-fill schwach")
3. **RelatedEntitiesSource** (Phase 5+): andere Basement-Entities zeigen 3-15 Räume erwartet
4. **VectorSearchSource** (Phase 5+): relevante Standards / Konventionen
5. **DomainPatternSource** (Phase 5+): Domain-Master-Patterns
6. **DoD ergibt sich**:
   - `rooms_count`: `"3..15"` (nicht 25-35 wie bei Wohngeschoss)
   - `parking_as_single_room`: `True`
   - `rooms_with_doors`: `">=70%"`
   - `clarification_needed: []`

Pipeline läuft (`effector.act`). Ergebnis: `rooms_count=27` → Validation verfehlt → User-Meldung:

> „DoD verfehlt: 27 Mini-Räume statt erwartet 3-15. Mögliche Ursache: Wand-Netzwerk-Lücken bei Parkbereich-Symbolen. Soll ich (a) alternativen Extraktor-Pfad nutzen, (b) die Eingabe als 'speziell, manuell prüfen' markieren?"

Das ist **nicht weniger Arbeit für den User** — aber die Arbeit landet zur richtigen Zeit (vor dem Sichten von 27 falschen Räumen) und mit klarer Optionen-Liste statt mit Frust. Detail: [`docs/STAR.de.md`](../STAR.de.md).

### Wann DoD-Recherche verzichtbar ist

Nicht jede Aktion braucht eine DoD. Heuristik:
- **Verzichtbar** bei reinen Lese-Operationen (Lookup, Suche)
- **Verzichtbar** in Stufe (a) — wenn der Mensch tut, weiß er's selbst
- **Pflicht** ab Stufe (b) — sobald das System vorschlägt, gehört
  ein Erfolgs-Maßstab dazu
- **Pflicht** bei jeder Schreibaktion in den Wahrheits-Speicher
- **Pflicht** bei Aktionen die Code-Patches betreffen (Self-Improvement-Loop, siehe [`06_SELF_IMPROVEMENT.md`](06_SELF_IMPROVEMENT.md))

### Verbindung zu den anderen Patterns

M5 ist nicht neu erfunden, sondern **die Synthese**:
- M1 (Prä-Lookup) liefert das Material für die DoD-Recherche
- M2 (Upstream) trägt DoD + Erfüllungsstand nach oben
  (lesson_aggregator lernt was DoDs gut formulieren)
- M3 (User-Gate) ist der Notausgang wenn DoD unklar bleibt
- M4 (Korpus-vor-Pipeline) ist DoD im Großen — Pipeline-Tweak
  bekommt nur grünes Licht wenn er DoD über alle Korpus-Pläne
  erfüllt

Alle vier Meta-Patterns greifen ineinander, aber **M5 ist das
verbindende Glied**, das aus "5 lose Bauteile" einen Organismus
macht. Ohne DoD ist das System reaktiv. Mit DoD ist es **bewertend**
— es weiß ob es gut war was es getan hat, ohne dass der Mensch es
ihm sagt.

## Das Mindestkriterium für ein lernendes System

Ein System ist **statisch** wenn (a) bis (e) leer bleiben — es tut
was es tut, niemand beobachtet, nichts ändert sich.

Ein System ist **lernend** wenn:
1. Beobachtung läuft (④)
2. Beobachtung speist Gedächtnis und/oder Nervensystem zurück
3. Aktionen wandern entlang (a) → (e), gemessen in
   Korrektur-Anteil über Zeit

Ein System ist **selbsterzeugend** wenn:
4. Neue Aktionen entstehen aus erkannten Lücken (Capability-Cluster
   → Self-Improvement-Worker → Code-Patch → Plan-Gate → live)

Stufe 1-3 ist heute gut umsetzbar. Stufe 4 ist heute Glue, wird
ernsthaft mit Sandbox-Stabilität (Podman/Container).

## Mapping zum Skelett (Stand: nach Phase 5)

| Bauteil | Realisierung im Skelett | Konsumenten-Verantwortung |
|---|---|---|
| ① Effektoren | `Effector` Protocol (Phase 1.3), `BaseEffector` (Phase 1.4), 5-Kontakt-Vertrag | echte `act()`-Logik, Vision-/Text-/Crawler-Calls |
| ② Gedächtnis | `EntityStore` (Phase 1.2), `Provenance` (Phase 4.0) | externe-Quelle-Anbindung, Vector-Store-Client, Cache-Layer |
| ③ Nervensystem | `DoDEngine` (Phase 2), `PlanGate` (Phase 3.1), `LifecycleManager` (Phase 3.2), `ActionOrchestrator` (Phase 3.3+5.0+5.1), `EventBus` (Phase 4.3+5.1) | `InsightService`-Implementation, Plan-Gate-UI |
| ④ Beobachtung | `TraceStore` (Phase 4.1), `LessonsAggregator` (Phase 4.2), OTel-Converter (Phase 4.3), Langfuse-Stub | Lift-Tracking, Pattern-Distillation, echter HTTP-Push |
| ⑤ Aktions-Lebenszyklus | `LifecycleManager` mit avg-Score-Promotion, AUTONOMOUS-Revision-Loop (Phase 5.0) | per-kind-Tuning, sichtbare Stage-UI, Demote-Strategien |

Die wichtigste Schnittstelle für Konsumenten ist ⑤: **eine UI die dem User die Stufe der Aktion zeigt**. Plan-Gate gates, aber zeigt nicht „diese Aktion ist bei (b) vorgeschlagen, nach N Approves wandert sie nach (c) geprüft". Konsumenten bauen diese Sichtbarkeit als Frontend obendrauf.

## Anwendung auf andere Domänen

Das Framework ist domänenneutral. Drei konkret implementierte Demo-Domains belegen das ([`docs/DEMOS.de.md`](../DEMOS.de.md), `examples/<demo>/`):

**Architekturbüro** (`architect_lite`):
- ① Effektor: `FloorPlanExtractor` mit `kind="extract_floor_plan"`
- ② Gedächtnis: `EntityStore` mit Floor-Plan-Entities (frei erfunden)
- ③ Nervensystem: voller Stack (Engine + Validator + PlanGate + Lifecycle + Orchestrator)
- ④ Beobachtung: Trace-Store + Lessons über alle Aktionen
- ⑤ Lebenszyklus: 4-Schritt-Walk durch PROPOSED → CHECKED → AUTONOMOUS

**Steuerberatung** (`tax_lite`):
- ① Effektor: `TaxReturnValidator` mit `kind="validate_tax_return"`
- ② Gedächtnis: Mandant-Entities (frei erfunden, mit `client_type=individual|gmbh`)
- Rest analog

**CFO-Office** (`cfo_lite`):
- ① Effektor: `QuarterlyCloseRunner` mit `kind="run_close_step"`
- ② Gedächtnis: Reporting-Perioden-Entities (`fiscal_year`, `quarter`)
- Rest analog

**Trenn-Test verifiziert**: alle drei Demos produzieren identische Pipeline-Counts (6 Aktionen / 6 Traces / 3 Lessons / 11 Events / 1 Transition). `tests/examples/test_cross_demo.py` ist der automatisierte Wächter — wenn er bricht, ist die Genericity gefährdet.

Weitere Domain-Beispiele die plausibel wären:

- **Anwaltskanzlei**: `kind="check_contract_clause"`, Entity = Mandat, Effektor prüft Vertragsklauseln
- **Krankenhaus (admin)**: `kind="propose_drg_code"`, Entity = Fall, Effektor schlägt DRG-Codierung vor (stage `(e)` AUTONOMOUS ausgeschlossen — Mensch immer im Pfad)
- **Forschungsgruppe**: `kind="cross_reference_paper"`, Entity = Paper, Effektor verlinkt auf ähnliche Arbeiten

Die Stärke des Frameworks: ein Team das in Domäne X arbeitet, kann sein System aufsetzen indem es **die fünf Bauteile** ausfüllt — die Architektur-Mechanik bleibt gleich, nur Inhalte ändern sich.

## Schlussbild

Wir bauen kein Domain-spezifisches Tool. Wir bauen die Vorlage.

```
   Domäne austauschbar
        ⇡
   Bauteile ① ② ③ ④ ⑤  konstant
        ⇡
   Gold-Patterns M1 M2 M3 M4 M5  konstant
        ⇡
   Mensch im Mittelpunkt  konstant
```

Was unten konstant bleibt, ermöglicht oben das Variieren. Das ist der Vertrag.
