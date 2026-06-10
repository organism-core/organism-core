*[🇩🇪 Deutsche Version](README.de.md)*

# Docs index

Full documentation of the organism-core Skelett. Start with
[`M5_WHITEPAPER.md`](M5_WHITEPAPER.md) for a single-document
overview.

## Whitepaper drafts (public-ready)

Consolidated, thematic whitepaper drafts. Public-suitable, no
internal cross-references.

| Doc | Content | Length |
|---|---|---|
| [`M5_WHITEPAPER.md`](M5_WHITEPAPER.md) | **Single-document whitepaper** for sharing — M5 pattern, architectural context, cross-domain verification, references | ~490 lines |
| [`STAR.md`](STAR.md) | DoD-engine deep-dive — six-source hierarchy, comparator semantics, cross-domain examples | ~350 lines |
| [`LIFECYCLE.md`](LIFECYCLE.md) | Plan gate + lifecycle state machine — stages `(a)→(e)`, transitions, ActionOrchestrator | ~270 lines |
| [`OBSERVABILITY.md`](OBSERVABILITY.md) | Trace + lessons + EventBus + OTel — full observation layer | ~330 lines |
| [`DEMOS.md`](DEMOS.md) | Cross-domain validation — three demo domains with identical pipeline counts | ~290 lines |
| [`REENTRANCE.md`](REENTRANCE.md) | Reserved pattern (trigger 0) — human consultation mid-execution via parent-child plans; positions organism-core on the protocol layer of the May 2026 convergence wave (Anthropic Outcomes + TML + Halo) | ~240 lines |
| [`PRODUCTION_DEFAULT.md`](PRODUCTION_DEFAULT.md) | Adoption lesson — explicit Plan/HITL/Dispatch is the production default; the autonomous reflex arc stays a research track | ~100 lines |
| [`MCP_DESIGN.md`](MCP_DESIGN.md) | MCP audit (no MCP code in the skeleton) + binding stateless-by-design constraints for any future adapter, aligned with the 2026-07-28 RC | ~80 lines |
| [`RECEIPTED_TRANSFER.md`](RECEIPTED_TRANSFER.md) | Receipted-transfer pattern — six contract elements for auditable data hand-offs between semi-autonomous tools, with an empirical five-class failure taxonomy | ~150 lines |

## Architecture concepts

Structural docs across eleven chapters. Written in German (see
[`ARCHITEKTUR/INDEX.en.md`](ARCHITEKTUR/INDEX.en.md) for the English
chapter index). Each chapter is generic (entkernt in Phase 6); pointers
to the whitepaper drafts above for implementation detail.

See [`ARCHITEKTUR/INDEX.en.md`](ARCHITEKTUR/INDEX.en.md) for the per-
chapter reading paths.

## Governance

| Doc | Content |
|---|---|
| [`STRATEGIE-EXTRACT.md`](STRATEGIE-EXTRACT.md) | Separation contract: what belongs in the Skelett and what does not; the genericity discipline |
| [`TRANSLATION_GUIDE.md`](TRANSLATION_GUIDE.md) | Two-language convention; consonant-suffix rule for German-origin identifiers |

## Reading paths by use case

### "I just want to understand what this is" (15 min)

- [`M5_WHITEPAPER.md`](M5_WHITEPAPER.md), abstract + sections 1-3

### "I want to understand the DoD approach" (30 min)

- [`M5_WHITEPAPER.md`](M5_WHITEPAPER.md), complete
- [`STAR.md`](STAR.md) for engine detail

### "I want to plug in my own domain" (1-2 hours)

- [`M5_WHITEPAPER.md`](M5_WHITEPAPER.md) — pattern overview
- [`DEMOS.md`](DEMOS.md) — template guide
- [`examples/tax_lite/`](../examples/tax_lite/) as a concrete model
- [`ARCHITEKTUR/05_REFLEXBOGEN.md`](ARCHITEKTUR/05_REFLEXBOGEN.md) —
  P1-P10 as a sanity check (German)

### "I'm an architect evaluating adoption" (2-3 hours)

- [`M5_WHITEPAPER.md`](M5_WHITEPAPER.md)
- [`ARCHITEKTUR/INDEX.en.md`](ARCHITEKTUR/INDEX.en.md) + the German
  chapters
- [`OBSERVABILITY.md`](OBSERVABILITY.md) for OTel integration
- [`STRATEGIE-EXTRACT.md`](STRATEGIE-EXTRACT.md) for governance

### "I want to read the implementation"

- Code under [`../src/organism/`](../src/organism/) module by module
- Tests in [`../tests/`](../tests/) as executable spec

## See also

- [`../README.md`](../README.md) — repo entry with quick start
- [`../CONTRIBUTING.md`](../CONTRIBUTING.md) — contribution and
  separation-test guidance
