# Translation dictionary — organism-core

> **Übersetzungsbuch** for the organism-core Skelett. A single source
> of truth for German→English term mappings used in this project.
> Hand this file to any translation tool (LLM, machine translator,
> human translator) before they start on the remaining German
> documents.

## How to use this dictionary

1. **Identifier translations are binding** — when an identifier
   appears in code or in cross-references, use the exact English
   identifier in this table. Do not invent alternatives.
2. **Concept translations are guidance** — prose can paraphrase, but
   keep the central term recognizable so cross-references stay
   readable.
3. **When a translation is ambiguous** — append the consonant suffix
   per the rule in
   [`TRANSLATION_GUIDE.md`](TRANSLATION_GUIDE.md) (first four distinct
   consonants of the German original, digraphs counted as one).
4. **German-only terms** — some terms have no clean English
   equivalent. Keep the German word with an English gloss in
   parentheses the first time it appears in a document.

## Suffix derivation rule (recap)

1. Take the German word.
2. Drop vowels (a, e, i, o, u, ä, ö, ü, y).
3. Treat common digraphs as one consonant: `ck`, `sch`, `ch`, `ng`,
   `pf`, `tz`.
4. Take the first four distinct consonants in order.
5. Lowercase, prepend with underscore.

If a German word has fewer than four distinct consonants, take what
exists. If the English translation is unambiguous (1:1 cognate or
close), the suffix is optional.

---

## Core architecture concepts

| German                | English                        | Suffix    | Notes |
|-----------------------|--------------------------------|-----------|-------|
| Skelett               | Skelett / reference implementation | —     | Keep as proper name of the repo / framework |
| Wesen                 | Wesen (being) / Cockpit        | `_wsn`    | Used metaphorically for the Cockpit. Keep German on first mention with gloss. |
| Effektor              | Effector                       | —         | 1:1, no suffix |
| Querier               | Querier                        | —         | English origin, used in both languages |
| Reflex                | Reflex                         | —         | Cognate |
| Reflexbogen           | Reflex arc                     | `_rfxbg`  | Architecture chapter 5 |
| Aktion                | Action                         | —         | Default; only add suffix if the same English noun has another German source in scope |
| Anatomie              | Anatomy                        | —         | Cognate |
| Nervensystem          | Nervous system                 | —         | Cognate |
| Gedächtnis            | Memory                         | `_gdcn`   | The architectural chapter "03_GEDAECHTNIS.md" |
| Lebenszyklus          | Lifecycle                      | —         | Cognate |
| Bauteil               | Building block                 | `_btl`    | M-pattern context — keep German on first mention |

## Process and pattern terms

| German                 | English                         | Suffix     | Notes |
|------------------------|---------------------------------|------------|-------|
| DoD-Recherche          | DoD-Recherche (DoD research)    | —          | Keep "DoD-Recherche" — it is the proper noun of the M5 engine |
| Recherche              | Research / lookup               | `_rchrch`  | When ambiguous |
| Verfehlung             | Failure / violation             | `_vrfhl`   | DoD-Verfehlung = DoD failure |
| Verfehlungs-Lesson     | Failure lesson                  | —          | Compound; use English as one term |
| Stufe                  | Stage                           | —          | Use "stage" consistently in lifecycle context |
| Steckbrief             | Entity profile                  | `_stbr`    | **Binding**: code identifier is `ENTITY_PROFILE_FILENAME_stbr` |
| Trenn-Test             | Separation test                 | `_trnnt`   | Keep "Trenn-Test" on first mention with gloss; thereafter "separation test" |
| Trenn-Vertrag          | Separation contract             | `_trnnv`   | Same approach |
| Lernen                 | Learning                        | —          | 1:1 |
| Lern-Loop / Lernschleife | Learning loop                  | —          | |
| Plan-Gate              | Plan gate                       | —          | English-coined term, used in both |
| Plan-Gate-Entry        | Plan-gate entry                 | —          | |
| Vier-Augen-Prinzip     | Four-eyes principle             | `_vrgn`    | German idiom; English variant exists |
| Reifegrad              | Maturity / readiness            | `_rfgrd`   | Architecture chapter 7 |
| Wahrheits-Speicher     | Truth store                     | `_wrhts`   | Concept term |
| Wahrheitsquelle        | Source of truth                 | —          | |
| Vorlage                | Template                        | —          | |
| Schicht                | Layer                           | —          | |
| Pflicht                | Mandatory / required            | —          | "Plan-Gate ist Pflicht" → "the plan gate is mandatory" |
| Vertrag                | Contract                        | —          | |

## M1-M5 meta-pattern names

| German                       | English                          | Suffix | Notes |
|------------------------------|----------------------------------|--------|-------|
| Prä-Lookup                   | Pre-lookup                       | —      | M1 |
| Upstream                     | Upstream                         | —      | M2 |
| User-Gate                    | User gate                        | —      | M3 |
| Korpus-vor-Pipeline          | Corpus-before-pipeline           | —      | M4 |
| Definition-of-Done / DoD     | Definition-of-Done / DoD         | —      | M5; keep DoD acronym |
| 5-Kontakt-Vertrag            | Five-contact contract            | —      | Effector protocol |
| 2-Kontakt-Vertrag            | Two-contact contract             | —      | Querier protocol |

## Lifecycle stage labels

| German                | English (used in code) | Notes |
|-----------------------|------------------------|-------|
| (a) manuell           | (a) MANUAL             | LifecycleStage.MANUAL |
| (b) vorgeschlagen     | (b) PROPOSED           | LifecycleStage.PROPOSED |
| (c) geprüft           | (c) CHECKED            | LifecycleStage.CHECKED |
| (d) routiniert        | (d) ROUTINE            | LifecycleStage.ROUTINE |
| (e) eigenständig      | (e) AUTONOMOUS         | LifecycleStage.AUTONOMOUS |

## Demo-domain vocabulary (kept in `examples/<domain>/`)

These are allowed inside the example directories only. They must
never appear in `src/organism/`.

| German             | English                | Notes |
|--------------------|------------------------|-------|
| Architekturbüro    | Architecture practice  | architect_lite |
| Steuerberatung     | Tax advisory           | tax_lite |
| Mandant            | Client                 | tax_lite (always preserve client-data privacy) |
| CFO-Office         | CFO office             | cfo_lite |
| Floor-Plan         | Floor plan             | architect_lite (English original) |
| Quartals-Close     | Quarterly close        | cfo_lite |

## Roles and titles

| German            | English             | Notes |
|-------------------|---------------------|-------|
| Kurator           | Curator             | "Mensch ist Kurator" → "Human is curator" |
| Vorschlag         | Proposal            | "KI ist Vorschlag" → "AI is proposal" |
| Mensch-in-the-Loop / HITL | Human-in-the-loop / HITL | Keep HITL acronym |

## Code identifiers — binding rules

| German identifier in code   | English-with-suffix              | Action |
|-----------------------------|----------------------------------|--------|
| (none remaining)            | `ENTITY_PROFILE_FILENAME_stbr` (constant) → `_entity_profile.md` (on-disk filename) | The `_stbr` consonant-suffix marks the historic German concept "Steckbrief"; the constant value and on-disk filename are both English. |

No German code identifiers exist in `src/organism/`. New identifiers must
follow the TRANSLATION_GUIDE convention.

## German strings in code

Any remaining German text inside Python string literals should be
translated to English. Audit command:

```bash
grep -rn '[äöüÄÖÜß]' src/
```

Comments may stay in German (per CONTRIBUTING.md), but identifiers
and user-visible strings (in error messages, log lines, returned
`reason` fields) must be English.

## Documents and their translation status

| Path                                 | EN          | DE              | Notes |
|--------------------------------------|-------------|-----------------|-------|
| `README.md`                          | ✅ primary   | `README.de.md`  | Done |
| `CONTRIBUTING.md`                    | ✅ primary   | `CONTRIBUTING.de.md` | Done |
| `docs/README.md`                     | ✅ primary   | `docs/README.de.md` | Done |
| `docs/STRATEGIE-EXTRACT.md`          | ✅ primary   | `docs/STRATEGIE-EXTRACT.de.md` | Done |
| `docs/TRANSLATION_GUIDE.md`          | ✅ primary   | —               | Convention doc, English only |
| `docs/TRANSLATION_DICTIONARY.md`     | ✅ primary   | —               | This file, English only |
| `docs/ARCHITEKTUR/INDEX.en.md`       | ✅ primary   | `ARCHITEKTUR/README.md` (German) | English chapter index for the 11 German chapters |
| `docs/ARCHITEKTUR/00_LEITBILD.md` … `10_LANDSCHAFT.md` | — | ✅ German only | Deep-dive chapters; English readers use `INDEX.en.md` |
| `docs/M5_WHITEPAPER.md`              | **TODO**    | (current is DE) | Largest; ~490 lines |
| `docs/STAR.md`                       | **TODO**    | (current is DE) | ~350 lines |
| `docs/LIFECYCLE.md`                  | **TODO**    | (current is DE) | ~270 lines |
| `docs/OBSERVABILITY.md`              | **TODO**    | (current is DE) | ~330 lines |
| `docs/DEMOS.md`                      | **TODO**    | (current is DE) | ~290 lines |
| `src/organism/*/README.md`           | ✅ primary   | `*/README.de.md`| All eight module READMEs done |
| `MEMORY.md`                          | German only | —               | Working journal — not translated |
| `.github/*` (issue / PR templates)   | German only | —               | Internal until external load |

## TODO items for follow-up translation tools

The five documents in the table above marked **TODO** are the
remaining bulk translation work:

1. **`docs/M5_WHITEPAPER.md`** (~490 lines) — single-document
   whitepaper. Highest priority; this is the share-friendly entry
   point for external readers.
2. **`docs/STAR.md`** (~350 lines) — DoD-engine deep dive.
3. **`docs/LIFECYCLE.md`** (~270 lines) — plan gate + lifecycle.
4. **`docs/OBSERVABILITY.md`** (~330 lines) — trace, lessons, OTel.
5. **`docs/DEMOS.md`** (~290 lines) — cross-domain validation.

### Translation workflow for each

For each file:

1. `cp docs/X.md docs/X.de.md` and add the cross-link header at the
   top of the German copy: `*[🇬🇧 English version](X.md)*`.
2. Translate the original `docs/X.md` to English. Use this
   dictionary for term mappings. Keep code blocks (`python … `,
   `bash … `, etc.) verbatim.
3. Add the English cross-link header at the top of `docs/X.md`:
   `*[🇩🇪 Deutsche Version](X.de.md)*`.
4. Verify cross-references inside the document still resolve (most
   links are intra-doc — they should not need adjustment because
   filenames are unchanged).
5. Sanity check: search the English file for any remaining `ä ö ü ß`
   characters — those indicate untranslated fragments.

## What to preserve verbatim

Even in English translation, keep these as-is:

- **Code blocks** (Python, YAML, bash). The Skelett's API names are
  English already.
- **Path references** (`src/organism/dod/`, `docs/STAR.md`, …).
- **Identifier names** (`DoDEngine`, `Cockpit`, `BaseEffector`, …).
- **Proper-noun German terms** when they are part of the Skelett's
  vocabulary: `Trenn-Vertrag`, `Wesen`, `Steckbrief` (with English
  gloss on first occurrence per document).
- **The repo name** `organism-core`.

## What never to translate

- Real German names appearing in commit messages, file headers, or
  author attributions.
- Quoted user feedback or domain-expert input.
- Configuration keys (`promote_after_n`, `fulfillment_score_pass`,
  etc.) — they are English already.
- File path segments (`tests/examples/test_cross_demo.py`).
