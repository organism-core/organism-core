*[🇩🇪 Deutsche Version](CONTRIBUTING.de.md)*

# Contributing to organism-core

## Setup

```bash
git clone https://github.com/organism-core/organism-core.git
cd organism-core
pip install -e ".[dev]"
```

## Run the tests

```bash
pytest tests/                                       # full suite
pytest tests/examples/test_cross_demo.py            # separation-test guard
python -m examples.architect_lite                   # demo run
```

## Separation contract ("Trenn-Vertrag")

Before every commit to the Skelett repo, apply this single test:

> **"Would the same logic make sense in a tax-advisory firm?"**

- ✅ Yes, with renamed variables → belongs in the Skelett
- ✅ Yes, with plugin points → belongs in the Skelett with explicit
  extension hooks
- ❌ No, would be useless there → does NOT belong in the Skelett

Detail: [`docs/STRATEGIE-EXTRACT.md`](docs/STRATEGIE-EXTRACT.md).

## Code conventions

- **Python ≥ 3.11**
- **Identifiers in English** (`Effector`, `Entity`, `Stage`); German
  comments are tolerated, German identifiers are not (with the
  documented consonant-suffix exception — see
  [`docs/TRANSLATION_GUIDE.md`](docs/TRANSLATION_GUIDE.md))
- **Typed dataclasses** instead of plain dicts where possible
- **`from __future__ import annotations`** in every new module
- **Pure functions + `dataclasses.replace`** instead of in-place
  mutation where possible
- **`Settings` classes** (admin-UI-friendly via `register_settings()`)
  for configurable values — no hidden constants
- **Defaults are documented** in `config/<component>.yaml` with
  comments

### Effectors — recommended idiom

Effectors inherit from [`BaseEffector`](src/organism/adapter/base.py)
and typically override only **`act`** (the side-effect method) and
**`define_done`** (DoD hints — return an empty dict when the DoD
engine drives derivation). The other three methods (`pre_load`,
`upstream`, `gate`) have safe defaults.

```python
from organism.adapter import BaseEffector

class MyTool(BaseEffector):
    name = "my_tool"

    def define_done(self, request, context):
        return {}  # DoD comes from the engine

    def act(self, request):
        return {"result": ...}  # the actual action
```

`BaseEffector.act()` raises `NotImplementedError` — deliberately not a
silent no-op, because no meaningful default exists for side-effect
methods. Forgetting to override `act` fails loudly at runtime.

### Read-only effectors

For pure lookups / queries / file reads (no side effects) there is
[`ReadEffector`](src/organism/adapter/base.py). It inherits from
`BaseEffector` with two differences:

- `define_done` returns an **empty dict** instead of a clarification
  blocker — reads do not need a safety gate via DoD (matches the
  M5-patch rule "DoD waivable for deterministic operations")
- Class attribute `read_only = True` as an introspection marker

```python
from organism.adapter import ReadEffector

class MyLookup(ReadEffector):
    name = "my_lookup"

    def act(self, request):
        return self.store.get(request)
```

`act` still raises `NotImplementedError` until overridden — the read
logic must be explicit. To turn a read-effector into a mutating one,
flip `read_only = False` and re-implement the other contacts as
needed.

### Querier — recommended idiom

For pure reads whose success is intrinsically defined (a todo list
has no "acceptance criterion"), there is a separate lineage:
[`BaseQuerier`](src/organism/query/base.py) + `QueryRunner`. The
protocol is reduced to two methods:

```python
from organism.query import BaseQuerier

class TodoQuerier(BaseQuerier):
    name = "todo"

    def query(self, request):
        return {"todos": [...]}
```

What Querier **does not** have (compared to Effector): `define_done`,
`upstream`, `gate`. Reads return data, write nothing. Provenance and
lessons are not emitted by the querier — the `QueryRunner` writes a
`QueryTrace`, which is sufficient for read-side observability. For
side-effect tools: `BaseEffector` plus `ActionOrchestrator`.

### Deterministic vs. probabilistic reads — decision boundary

Not every read fits the `Querier` path. The heuristic from the
M5 patch:

| Read type | Examples | Path |
|---|---|---|
| **Deterministic** (no room for interpretation) | SQL lookup, file read, todo list, exact schema match | `BaseQuerier` + `QueryRunner` |
| **Probabilistic** (room for interpretation, needs an acceptance criterion) | OCR, vector-search ranking, classification, plan recognition | `BaseEffector` (or `ReadEffector` as a niche) + `ActionOrchestrator` |
| **Side-effect action** | File writes, API calls with POST / PUT / DELETE, email sending | `BaseEffector` + `ActionOrchestrator` |

Rule of thumb: **"Can the result be wrong without raising an
exception?"** Yes → Effector path with DoD validation. No → Querier
path.

`ReadEffector` is the bridging class for probabilistic reads —
marked via `read_only = True` but retaining the five-method protocol
surface so `ActionOrchestrator` runs DoD validation against it.

### Alternative

Implement the `Effector` protocol directly — all five methods
manually. Only useful when neither `BaseEffector` nor `ReadEffector`
fits for inheritance reasons. For reads: implement the `Querier`
protocol directly instead of inheriting from `BaseQuerier`.

## What belongs in the Skelett (and what does not)

See [`docs/STRATEGIE-EXTRACT.md`](docs/STRATEGIE-EXTRACT.md). In short:

- **Yes**: domain-independent patterns, data types, service layers
- **No**: concrete LLM / vector-DB / OTel-SDK bindings (they belong in
  consumers)
- **No**: domain-specific vocabulary in `src/` (`projekt`, `mandant`,
  `cost-center`)
- **No**: real or anonymized domain data

## PR process

1. Branch from `main`: `git checkout -b feature/my-change`
2. Code + tests + doc update
3. Apply the separation test mentally (see above)
4. Open a PR using the template in
   `.github/pull_request_template.md`
5. CI must be green (tests + cross-domain verification + three demo
   smoketests)
6. Sign the CLA — either by adding a `Signed-off-by:` trailer to
   your commits or by stating agreement in the PR. See
   [`CLA.md`](CLA.md) for the full text.

## Where to find help

- [`docs/M5_WHITEPAPER.md`](docs/M5_WHITEPAPER.md) — single-document
  overview
- [`docs/README.md`](docs/README.md) — doc index with reading paths
- [`docs/ARCHITEKTUR/INDEX.en.md`](docs/ARCHITEKTUR/INDEX.en.md) —
  English index for the German architecture chapters
- [`docs/TRANSLATION_GUIDE.md`](docs/TRANSLATION_GUIDE.md) — two-
  language convention
- Issues tagged `question` for open discussion
