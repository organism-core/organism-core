# v0.3.0 — The Advanced Agentic Harness

> Source file for the GitHub release body (copy verbatim into
> Releases → Draft a new release → Tag `v0.3.0` @ `main`). Links are
> absolute so they resolve inside the release page.

This release repositions organism-core honestly against the
June-2026 landscape and adds two new pattern chapters. No breaking
API changes; 900 tests green (was 712 at v0.2.0).

## Repositioning — what we claim, what we don't

The README now frames organism-core as **The Advanced Agentic
Harness** and states the claim precisely: the differentiator is not
any single primitive but the **fused execution path** — DoD research
→ plan gate → earned autonomy → validation → persistent lessons.
Three primitives carry it (claims dated, June 2026):

1. **Persistent cross-arm lessons** — failure insights re-injected at
   the next derivation, including across action types.
2. **Score-driven autonomy per action type** — stages `(a)→(e)`
   earned from validation history (the model the literature now calls
   the Digital Apprentice, arXiv 2606.04321 — published there as
   concept; shipped here as tested code).
3. **Auto-demotion as a security feature** — granted autonomy is
   revocable by construction; drift demotes automatically. This is
   the harness-level answer to the irrevocable-autonomy risk in the
   OWASP Agentic Top 10 (2026).

Just as explicitly, the README stops selling commodity as
differentiation: HITL plan gating (every major platform ships it;
EU AI Act Art. 14 mandates oversight anyway) and file-first
YAML/Markdown memory are named as load-bearing building blocks, not
USPs. The cross-domain genericity guard is reclassified as an
architecture fitness function.

## New pattern chapters

- **[Receipted Transfer](https://github.com/organism-core/organism-core/blob/main/docs/RECEIPTED_TRANSFER.md)**
  — auditable data hand-offs between semi-autonomous tools: six
  contract elements (declared routes, append-only receipts,
  fail-loud registry, both-sided schema check, provenance
  propagation, gate hook) derived from an empirical five-class
  failure taxonomy observed in production. Four of the five failure
  classes raise no exception — only contracts that make *absence*
  visible catch them.
- **[Production Default](https://github.com/organism-core/organism-core/blob/main/docs/PRODUCTION_DEFAULT.md)**
  — adoption lesson from the first production consumer: explicit
  `propose → plan gate (HITL) → dispatch` is the production
  standard; the autonomous reflex arc stays a research track behind
  evidence triggers.
- **[MCP Design Constraints](https://github.com/organism-core/organism-core/blob/main/docs/MCP_DESIGN.md)**
  — audit result (no MCP code in the skeleton; the 2026-07-28
  release candidate breaks nothing here) plus binding
  stateless-by-design constraints for any future adapter: no
  deprecated Roots/Sampling/Logging, async via MCP Tasks, plan-gate
  approval mappable to MCP Elicitation.

## Landscape update

[`docs/ARCHITEKTUR/10_LANDSCHAFT.md`](https://github.com/organism-core/organism-core/blob/main/docs/ARCHITEKTUR/10_LANDSCHAFT.md)
is re-graded against June 2026 (deepagents RubricMiddleware, Foundry
auto-rubrics, Anthropic Outcomes beta, MCP/A2A consolidation under
the Linux Foundation, OpenAI Evals/Agent Builder sunset 2026-11-30),
including an evaluator guideline: mechanical checks before LLM
judging, with periodic human calibration (GER-Eval).

## README & repo hygiene

- CI / license / Python badges; HTTPS clone URLs; dead links removed.
- Architecture diagram (Mermaid), verified against the actual
  orchestrator control flow.
- A runnable ~40-line "define your own effector" example, guarded by
  `tests/examples/test_readme_example.py` so API drift breaks it
  visibly.
- German project terms (Skelett, Wesen, DoD-Recherche) glossed at
  first use, with a mini-glossary in
  [`docs/TRANSLATION_GUIDE.md`](https://github.com/organism-core/organism-core/blob/main/docs/TRANSLATION_GUIDE.md).
- The repo practices the memory discipline its docs argue for:
  journal files split into an index plus topic files of ≤200 lines.

## organism-core Cloud (in evaluation)

A hosted approval gate & audit-report layer on top of the framework
— EU-hosted, GDPR-first, aimed at EU AI Act Art. 14 evidence — is
under evaluation. No dates, no pricing; we are measuring demand
before building. Waitlist: [brachia.dev](https://brachia.dev) ·
`info@brachia.dev`. The framework itself stays AGPL-3.0 and
self-hostable.

## License change

From this release, organism-core is licensed under **GNU AGPL-3.0**
(was Apache 2.0 up to v0.2.0), **dual-licensed**: free under the
AGPL for everyone, with a commercial exception available for
closed-source / SaaS use that doesn't want the network-copyleft
obligation (`info@brachia.dev`). The open-source path stays open
permanently — the standard sell-exceptions model, made possible by
the contributor CLA. See [`LICENSE`](https://github.com/organism-core/organism-core/blob/main/LICENSE)
and the README license section.

---

**Full diff:** [v0.2.0...v0.3.0](https://github.com/organism-core/organism-core/compare/v0.2.0...v0.3.0)
