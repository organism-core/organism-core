*[🇬🇧 English version](CONTRIBUTING.md)*

# Contributing zu organism-core

## Setup

```bash
git clone https://github.com/organism-core/organism-core.git
cd organism-core
pip install -e ".[dev]"
```

## Tests laufen lassen

```bash
pytest tests/                                      # Vollständige Suite
pytest tests/examples/test_cross_demo.py          # Trenn-Test-Wächter
python -m examples.architect_lite                  # Demo-Lauf
```

## Trenn-Vertrag

Vor jedem Commit ins Skelett-Repo:

> **„Würde dieselbe Logik in einer Steuerberatung Sinn ergeben?"**

- ✅ Ja, mit umbenannten Variablen → gehört ins Skelett
- ✅ Ja, mit Plugin-Punkten → gehört ins Skelett mit klaren Erweiterungs-Stellen
- ❌ Nein, wäre dort nutzlos → gehört NICHT ins Skelett

Detail: [`docs/STRATEGIE-EXTRACT.de.md`](docs/STRATEGIE-EXTRACT.de.md).

## Code-Konventionen

- **Python ≥ 3.11**
- **Identifier auf Englisch** (`Effector`, `Entity`, `Stage`), Kommentare auf Deutsch erlaubt
- **Typed dataclasses** statt plain dicts wo möglich
- **`from __future__ import annotations`** in jedem neuen Modul
- **Pure Funktionen + `dataclasses.replace`** statt In-Place-Mutation wo möglich
- **`Settings`-Klassen** (admin-UI-fähig via `register_settings()`) für konfigurierbare Werte — keine versteckten Konstanten
- **Defaults sind dokumentiert** in `config/<component>.yaml` mit Kommentaren

### Effektoren — empfohlenes Idiom

Effektoren erben von [`BaseEffector`](src/organism/adapter/base.py) und überschreiben in der Regel nur **`act`** (die Side-Effect-Methode) und **`define_done`** (DoD-Hinweise — leeres Dict wenn die DoD-Engine die Definition liefert). Die anderen drei Methoden (`pre_load`, `upstream`, `gate`) haben sichere Defaults.

```python
from organism.adapter import BaseEffector

class MyTool(BaseEffector):
    name = "my_tool"

    def define_done(self, request, context):
        return {}  # DoD kommt aus der Engine

    def act(self, request):
        return {"result": ...}  # die eigentliche Aktion
```

`BaseEffector.act()` wirft `NotImplementedError` — bewusst kein Silent-No-Op, weil keine sinnvolle Default-Aktion für Side-Effect-Methoden existiert. Wer `act` vergisst zu überschreiben, fällt laut auf.

### Read-Only-Effektoren

Für reine Lookups / Queries / File-Reads (keine Side-Effects) gibt es [`ReadEffector`](src/organism/adapter/base.py). Es erbt von `BaseEffector` mit zwei Unterschieden:

- `define_done` liefert **leeres Dict** statt clarification-Blocker — Reads brauchen keinen Safety-Gate via DoD (passt zum M5-Patch „DoD verzichtbar bei deterministischen Operationen")
- Klassen-Attribut `read_only = True` als Marker für Introspektion

```python
from organism.adapter import ReadEffector

class MyLookup(ReadEffector):
    name = "my_lookup"

    def act(self, request):
        return self.store.get(request)
```

`act` wirft weiterhin `NotImplementedError` wenn nicht überschrieben — die Read-Logik muss explizit kommen. Wer einen Read-Effektor zu einem mutierenden umbauen will, kippt `read_only = False` und implementiert die anderen Contacts neu.

### Querier — empfohlenes Idiom

Für reine Reads, deren Erfolg intrinsisch definiert ist (eine Todo-Liste hat keine „Akzeptanz-Kriterien"), gibt es eine eigene Lineage: [`BaseQuerier`](src/organism/query/base.py) + `QueryRunner`. Das Protocol ist auf zwei Methoden geschrumpft:

```python
from organism.query import BaseQuerier

class TodoQuerier(BaseQuerier):
    name = "todo"

    def query(self, request):
        return {"todos": [...]}
```

Was Querier **nicht** hat (im Gegensatz zu Effector): `define_done`, `upstream`, `gate`. Reads liefern Daten zurück, schreiben nichts. Provenance/Lessons werden nicht vom Querier emittiert — der `QueryRunner` schreibt einen `QueryTrace`, das genügt für Read-Beobachtbarkeit. Für Side-Effect-Tools: `BaseEffector` plus `ActionOrchestrator`.

### Deterministische vs probabilistische Reads — Entscheidungs-Boundary

Nicht jeder Read passt in den `Querier`-Pfad. Die Heuristik aus dem M5-Patch:

| Read-Typ | Beispiele | Pfad |
|---|---|---|
| **Deterministisch** (kein Interpretationsspielraum) | SQL-Lookup, Datei-Read, Todo-Liste, exakter Schema-Match | `BaseQuerier` + `QueryRunner` |
| **Probabilistisch** (Interpretationsspielraum, braucht Akzeptanz-Kriterium) | OCR, Vector-Search-Ranking, Klassifikation, Plan-Erkennung | `BaseEffector` (oder `ReadEffector` als Nische) + `ActionOrchestrator` |
| **Side-Effect-Aktion** | Datei-Schreiben, API-Call mit POST/PUT/DELETE, E-Mail-Versand | `BaseEffector` + `ActionOrchestrator` |

Faustregel: **„Kann das Ergebnis falsch sein, ohne dass ein Exception fliegt?"** Ja → Effector-Pfad mit DoD-Validierung. Nein → Querier-Pfad.

`ReadEffector` ist die Brücken-Klasse für probabilistische Reads — markiert via `read_only = True`, aber behält den 5-Methoden-Protocol-Surface, damit `ActionOrchestrator` mit DoD-Validierung läuft.

### Alternative

Direkt das `Effector`-Protocol implementieren — alle 5 Methoden manuell. Nur sinnvoll wenn weder `BaseEffector` noch `ReadEffector` aus Vererbungs-Gründen passen. Für Reads: direkt `Querier`-Protocol implementieren statt von `BaseQuerier` zu erben.

## Was ins Skelett gehört (und was nicht)

Siehe [`docs/STRATEGIE-EXTRACT.de.md`](docs/STRATEGIE-EXTRACT.de.md). Kurz:

- **Ja**: domänen-unabhängige Patterns, Datentypen, Service-Schichten
- **Nein**: konkrete LLM-/Vector-DB-/OTel-SDK-Anbindungen (gehören in Konsumenten)
- **Nein**: domänen-spezifisches Vokabular im `src/` (`projekt`, `mandant`, `cost-center`)
- **Nein**: echte oder anonymisierte Domain-Daten

## PR-Prozess

1. Branch von `main`: `git checkout -b feature/my-change`
2. Code + Tests + Doku-Update
3. Trenn-Test im Kopf durchgehen (siehe oben)
4. PR mit dem Template aus `.github/pull_request_template.md`
5. CI muss grün sein (Tests + Cross-Domain-Verifikation + 3 Demo-Smoketests)
6. CLA unterzeichnen — entweder per `Signed-off-by:`-Trailer in den
   Commits oder per Bestätigung im PR. Volltext siehe
   [`CLA.md`](CLA.md).

## Wo Hilfe finden

- [`docs/M5_WHITEPAPER.de.md`](docs/M5_WHITEPAPER.de.md) — single-document Überblick
- [`docs/README.de.md`](docs/README.de.md) — Doc-Index mit Lesepfaden
- [`docs/ARCHITEKTUR/05_REFLEXBOGEN.md`](docs/ARCHITEKTUR/05_REFLEXBOGEN.md) — P1-P10 Pattern-Pflichten für Effektoren
- Issues mit Label `question` für allgemeine Diskussionen
