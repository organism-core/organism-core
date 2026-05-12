*[🇩🇪 Deutsche Version](README.de.md)*

# memory/

Entity-memory pattern: one directory per entity containing
`_entity_profile.md` (YAML frontmatter + free text) plus subordinate
indices for attached artifacts. Schema-free — fields are optional,
new fields are allowed at any time.

The in-code identifier `ENTITY_PROFILE_FILENAME_stbr` carries the
documented `_stbr` consonant-suffix convention (see
[`docs/TRANSLATION_GUIDE.md`](../../../docs/TRANSLATION_GUIDE.md)).

**Phase 1**: pattern implementation, free of domain-specific fields.

**Separation test ✓** — a tax-advisory firm would manage clients
this way (client instead of entity, advisor instead of owner). The
pattern is schema-free and generic.
