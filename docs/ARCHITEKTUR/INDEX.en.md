# Architecture chapters — English index

*[🇩🇪 Deutsche Version: README.md](README.md)*

The eleven architecture chapters in this directory are written in
**German**. They are the conceptual deep-dive into how the parts of the
Skelett interact — the long-form companion to the English
implementation docs in [`docs/M5_WHITEPAPER.md`](../M5_WHITEPAPER.md)
and the per-component whitepapers.

If your German is rusty, the English Whitepapers cover the same
substance with a focus on the patterns the Skelett implements. The
German chapters are the *why-and-how* behind those patterns, in the
original author's voice.

## Chapter index

| # | File | What it answers | Reading time |
|---|---|---|---|
| 0 | [`00_LEITBILD.md`](00_LEITBILD.md) | Guiding principles — what is being built, and why this way | 5 min |
| 1 | [`01_ANATOMIE.md`](01_ANATOMIE.md) | Anatomy — which parts exist, what each does | 10 min |
| 2 | [`02_NERVENSYSTEM.md`](02_NERVENSYSTEM.md) | Nervous system — how the parts coordinate; the service layer | 10 min |
| 3 | [`03_GEDAECHTNIS.md`](03_GEDAECHTNIS.md) | Memory — where the truth lives; entity stores and provenance | 10 min |
| 4 | [`04_LERNEN.md`](04_LERNEN.md) | Learning — how the system improves; human-loop, plan-gate, lesson aggregation | 10 min |
| 5 | [`05_REFLEXBOGEN.md`](05_REFLEXBOGEN.md) | Reflex arc — mandatory patterns (entity-profile-first, provenance-required, ...) | 10 min |
| 6 | [`06_SELF_IMPROVEMENT.md`](06_SELF_IMPROVEMENT.md) | Self-improvement loop — what gets tracked for reinforcement-style learning | 5 min |
| 7 | [`07_REIFEGRAD.md`](07_REIFEGRAD.md) | Maturity — a 2-axis assessment framework for component readiness | 10 min |
| 8 | [`08_GOLD_PATTERNS.md`](08_GOLD_PATTERNS.md) | Gold patterns — high-leverage architectural decisions | 10 min |
| 9 | [`09_FRAMEWORK.md`](09_FRAMEWORK.md) | Universal framework — five building blocks + action lifecycle, portable to other domains | 10 min |
| 10 | [`10_LANDSCHAFT.md`](10_LANDSCHAFT.md) | Landscape — adopt vs. inspiration vs. USP; concrete building blocks (Skills, Langfuse, E2B, ...) | 15 min |

## When to read what

| Goal | Start here |
|---|---|
| First overview of the Skelett | English Whitepaper ([`docs/M5_WHITEPAPER.md`](../M5_WHITEPAPER.md)) — don't start here |
| Understand the patterns conceptually | Chapter 0 → 1 → 9 (in this order) |
| Understand the truth model | Chapter 3 |
| Understand the learning loops | Chapter 4 + 6 |
| See where the Skelett sits in the wider ecosystem | Chapter 10 |
| Implement a consumer | Chapter 9 (framework) + the English [`CONTRIBUTING.md`](../../CONTRIBUTING.md) |

## Why these chapters stay in German

They were written in German first and reflect the original author's
conceptual journey. A translation would risk losing nuance (German
allows precise compound terms like *"Reflexbogen"*, *"Steckbrief"*,
*"Verfehlungs-Lesson"* that have no clean English equivalent without
a paragraph of context). The English Whitepapers absorb the practical
content; the German chapters preserve the conceptual reasoning.

See [`docs/TRANSLATION_GUIDE.md`](../TRANSLATION_GUIDE.md) for the
broader two-language policy of this repo.
