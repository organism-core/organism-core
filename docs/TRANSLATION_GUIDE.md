# Translation Guide

The Skelett is being prepared for two-language publication: **English
as primary** (default for GitHub readers) with **German parallel
versions** preserved for the original native-text record.

## File-naming convention

Side-by-side translations use a language-suffix:

```
README.md              English (primary)
README.de.md           German parallel
docs/STAR.md           English (primary)
docs/STAR.de.md        German parallel
src/organism/memory/README.md      English (primary)
src/organism/memory/README.de.md   German parallel
```

Both versions cross-link at the top:

```markdown
*[🇩🇪 Deutsche Version](README.de.md)*

# organism-core
...
```

## Code-identifier convention — consonant suffix for German originals

Where a German source term has been translated into an English identifier
and the translation might be ambiguous (multiple German words could map
to the same English word), the German original is preserved via a
consonant-suffix:

```python
# German "Steckbrief" -> English "entity_profile"
# Both could plausibly back-translate to several German words.
# Disambiguation: append the first four distinct consonants of the
# German original.
ENTITY_PROFILE_FILENAME_stbr = "_entity_profile.md"
```

### Suffix derivation rule

1. Take the German original word.
2. Drop vowels (a, e, i, o, u, ä, ö, ü) and the letter y.
3. Treat common digraphs as one consonant: `ck`, `sch`, `ch`, `ng`, `pf`, `tz`.
4. Take the first four distinct consonants in order.
5. Lowercase, prepend with underscore.

If the German word has fewer than four distinct consonants, take what
exists. The suffix is purely a disambiguator — readability of the
English identifier is the primary concern.

### Examples

| German original | Consonants extracted | Suffix    | English identifier example |
|-----------------|----------------------|-----------|----------------------------|
| Steckbrief      | S, T, B, R           | `_stbr`   | `ENTITY_PROFILE_FILENAME_stbr` |
| Wesen           | W, S, N              | `_wsn`    | `cockpit_wesen_wsn` (concept term) |
| Gedächtnis      | G, D, C(h), N        | `_gdcn`   | `memory_gdcn` (concept term) |
| Aktion          | K, T, N              | `_ktn`    | `action_ktn` (only if needed) |
| Effektor        | F, K, T, R           | `_fktr`   | usually unnecessary — `Effector` is unambiguous |
| Reflex          | R, F, L, X           | `_rflx`   | usually unnecessary — `Reflex` is unambiguous |
| Lebenszyklus    | L, B, N, S           | `_lbns`   | usually unnecessary — `Lifecycle` is unambiguous |

### When the suffix is NOT needed

When the English word has only one plausible German back-translation,
skip the suffix. Examples:

- `Effector` ← `Effektor` (1:1 mapping, no ambiguity)
- `Lifecycle` ← `Lebenszyklus` (1:1)
- `Reflex` ← `Reflex` (cognate)

The suffix is a tool against silent ambiguity, not a rule against
clean naming. Use it where a back-translation actually could go
multiple ways.

### Concept terms vs identifiers

For concept terms in docstrings ("Wesen", "Gedächtnis") — keep the
German word in quotes with a brief English gloss the first time it
appears in a docstring:

```python
"""CockpitBuilder — fluent assembly for the headless UI "Wesen"
(German "being"; the entity that hovers over the tools)."""
```

For runtime identifiers, follow the suffix rule.

## Migration path for renamed identifiers

For projects that already shipped a German identifier and need to
rename it to the English-with-suffix form without breaking consumers,
keep the old identifier as a **deprecated alias** during the migration
window:

```python
# new — primary name going forward
ENTITY_PROFILE_FILENAME_stbr = "_entity_profile.md"

# legacy alias, kept for backward compatibility — remove in a future
# major release after consumers have migrated
OLD_GERMAN_NAME = ENTITY_PROFILE_FILENAME_stbr
```

Mark such aliases in a comment with the legacy date and a target
removal version. This repo itself ships no legacy aliases — the
convention is documented here for downstream forks that may need it.

## Which docs are translated, which are not

| Document            | English | German parallel | Notes |
|---------------------|---------|-----------------|-------|
| `README.md`         | ✅       | `README.de.md`  | Primary entry |
| `CONTRIBUTING.md`   | ✅       | `.de.md`        | |
| `docs/M5_WHITEPAPER.md` | ✅   | `.de.md`        | Share-document |
| `docs/STAR.md`      | ✅       | `.de.md`        | |
| `docs/LIFECYCLE.md` | ✅       | `.de.md`        | |
| `docs/OBSERVABILITY.md` | ✅   | `.de.md`        | |
| `docs/DEMOS.md`     | ✅       | `.de.md`        | |
| `docs/README.md`    | ✅       | `.de.md`        | Doc index |
| `docs/STRATEGIE-EXTRACT.md` | ✅ | `.de.md`     | Governance |
| `src/organism/*/README.md` | ✅ | `.de.md`        | Per-module docs |
| `docs/ARCHITEKTUR/` | TOC only (`INDEX.en.md`) | full German (existing) | Architecture deep-dive stays in German; English readers get a chapter index |
| `MEMORY.md`         | German only | —          | Working journal, not a published document |
| Issue/PR templates  | German only | —          | Internal until external load |
