*[🇩🇪 Deutsche Version](STRATEGIE-EXTRACT.de.md)*

# Strategy and separation contract ("Trenn-Vertrag")

> Governance principles of the organism-core Skelett. What belongs
> here, and what does not?

## Mission

organism-core is a **reference implementation** for DoD-driven multi-
tool architectures. It ships an opinionated pattern set that works as
a single codebase — not a generic toolkit that supports every
pattern.

Consumers extend the Skelett for their concrete domain (see
[`DEMOS.md`](DEMOS.md) for templates). The Skelett itself stays
**domain-neutral**.

## Separation test (mandatory)

Before every commit to the Skelett repo:

> **"Would the same logic make sense in a tax-advisory firm?"**

- Yes, with renamed variables → belongs in the Skelett
- Yes, but only with plugin points → belongs in the Skelett with
  explicit extension hooks
- No, would be useless there → does NOT belong in the Skelett

When in doubt: **do not commit**. Leave the question open, and answer
the separation test by writing a mini-demo (see `examples/tax_lite/`
or `examples/cfo_lite/` as templates).

The separation test is verified automatically via
`tests/examples/test_cross_demo.py`: all three demo domains
(architecture practice, tax advisory, CFO office) must produce
identical pipeline counts. If one diverges, the pipeline has become
domain-specific.

## What belongs in the Skelett

- DoD engine + validator + six source patterns ([`STAR.md`](STAR.md))
- Plan gate + lifecycle state machine + orchestrator
  ([`LIFECYCLE.md`](LIFECYCLE.md))
- Provenance + trace + lessons + EventBus + OTel converter
  ([`OBSERVABILITY.md`](OBSERVABILITY.md))
- Settings layer (admin-UI-friendly)
- Effector protocol (five-contact contract)
- Demo domains as a genericity discipline

## What does NOT belong in the Skelett

### Real domain data

Never real or anonymized entity profiles ("Steckbriefe") / client
data / floor plans / bookings / etc. **Structural patterns leak
through anonymization** — whoever knows the data recognizes it even
in "anonymized" form.

Demo data under `examples/` is **made up**. There is no anonymization
pipeline from a real source.

### Domain-specific vocabulary in `src/`

In Skelett code (`src/organism/`), no domain-specific terms. Generic
terms are:

- ✓ `Entity`, `EntityStore`, `Effector`, `Action`, `Stage`, `Lesson`,
  `Trace`
- ✗ `Projekt`, `Bauherr`, `Gewerk` (architecture-practice-specific)
- ✗ `Mandant`, `Buchung`, `Steuerklasse` (tax-specific)
- ✗ `Cost-Center`, `Budget-Variance` (CFO-specific)

In `examples/<domain>/`, domain-specific terms are of course allowed
— that is the point of the demos.

### Domain-specific hard-coded logic

No `if entity.type == "wohnbau"` branches in the Skelett. Domain
logic belongs in the consumers' effectors or in the
`frontmatter.dod.criteria` block of the entity profiles.

### Tools of the day

No concrete LLM-provider SDK bindings, no concrete vector-DB clients,
no concrete OTel exporters in the Skelett. Instead: stub sources
(Phase 2.3) with a stable API that consumers wire up against their
own tooling choice.

## What consumers add

| Layer | Skelett provides | Consumer provides |
|---|---|---|
| Effector implementation | Protocol + BaseEffector + five-contact contract | concrete `act()` logic with LLM / vision / API calls |
| Vector store | `VectorSearchSource` stub | real vector client (ChromaDB, Pinecone, Weaviate) |
| External source binding | EntityStore pattern | mount reader for DMS / filesystem / API |
| Plan-gate UI | API + state machine | web cockpit with notifications |
| OTel export | structure-only converter | exporter to Langfuse / Jaeger / Phoenix |
| Self-improvement worker | concept doc in [`ARCHITEKTUR/06_SELF_IMPROVEMENT.md`](ARCHITEKTUR/06_SELF_IMPROVEMENT.md) | sandbox implementation (E2B / Firecracker / container) |

## Format conventions

### Truth is file-based

Structured data in the truth store is **YAML or Markdown**. No JSON
(comments not allowed), no pickle, no proprietary binary format.

Vector stores are allowed as an index layer — but never as the truth
source. "Imagine deleting the vector DB — the system survives, the
index would be rebuilt from EntityStore."

### Provenance on every AI output

Every AI-generated entry in the truth store has a `_provenance`
block:

```yaml
groesse_qm: 1850
_provenance:
  author: my_effector
  source: "Vision call against PDF X dated 2026-04-12"
  confidence: 0.85
  validated_by_user: false
  timestamp: "2026-04-12T14:32:00+00:00"
```

Without provenance, an entry is not traceable. On conflicts between
two statements, `validated_by_user` decides (true wins over false),
then `confidence`. Detail: [`OBSERVABILITY.md`](OBSERVABILITY.md).

### The plan gate is not optional

Write operations with external effect always go through the plan
gate (from lifecycle stage `(b) PROPOSED` upward). Bypassing it is a
bug. Test: can the user undo the action without `git revert`? If not
→ it must go through the plan gate.

Detail: [`LIFECYCLE.md`](LIFECYCLE.md).

## Success definition

The Skelett is successful when:

1. An effector that was good six months ago is better today —
   **without anyone changing the effector itself**. Improvement comes
   from lessons emitted by other effectors, from plan-gate approvals,
   from master patterns.
2. A new effector can be plugged in within a day, because the nervous
   system (engine, validator, plan gate, lessons aggregator, event
   bus) is already provided by the Skelett.
3. A query to the system never returns "I don't know" — it either
   answers, or replies "this source is missing — should I create it?"
   (the NEEDS_CLARIFICATION path, see [`STAR.md`](STAR.md)).

## License and ownership

- **Skelett repo** (`organism-core`): GNU AGPL-3.0, dual-licensed
  (commercial exception available via `info@brachia.dev`). Apache 2.0
  up to v0.2.0; AGPL-3.0 from v0.3.0 onward.
- **Consumer repos**: each its own license choice. They consume
  `organism-core` as a dependency or via code adoption.

Nobody outside the consumer organization gets access to consumer-
specific data — that is the precondition for the file-first memory
philosophy.
