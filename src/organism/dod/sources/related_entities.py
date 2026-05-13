"""Related-entities source — pulls criteria from sibling entities
that the heuristic considers part of the same cluster.

Two cluster heuristics ship in parallel, each as its own source
instance so the engine writes separate provenance buckets:

- ``MODE_PREFIX``: entities whose id shares the same prefix
  (e.g. ``343_alpha`` and ``343_beta`` cluster under prefix ``343``).
  Trennzeichen ist :attr:`RelatedEntitiesSettings.prefix_separator`
  (default ``"_"``). Provenance bucket ``related_entities:prefix``.
- ``MODE_TAGS``: entities whose frontmatter ``tags: [...]`` list
  shares at least :attr:`RelatedEntitiesSettings.tags_min_overlap`
  entries with the focal entity. Provenance bucket
  ``related_entities:tags``.

Each instance reads ``context[CONTEXT_KEY_ENTITY_ID]`` to identify
the focal entity, iterates the store, picks related entities by its
mode, and re-injects their ``dod.criteria`` with reduced weight
(``cross_entity_weight_factor``). Criteria already present in the
current DoD are dropped.

Stub semantics: ``RelatedEntitiesSource()`` with no store returns an
empty contribution and writes no provenance — required for the
protocol-compliance tests.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from organism.dod.settings import RelatedEntitiesSettings
from organism.dod.types import Criterion, DoD, SourceContribution
from organism.memory import EntityStore

CONTEXT_KEY_ENTITY_ID = "entity_id"
FRONTMATTER_KEY = "dod"


class RelatedEntitiesSource:
    """Pulls DoD criteria from cluster-sibling entities."""

    MODE_PREFIX = "prefix"
    MODE_TAGS = "tags"
    _MODES = frozenset({MODE_PREFIX, MODE_TAGS})

    name = "related_entities"

    def __init__(
        self,
        store: EntityStore | None = None,
        *,
        settings: RelatedEntitiesSettings | None = None,
        lookup_mode: str | None = None,
    ) -> None:
        self.store = store
        self.settings = settings or RelatedEntitiesSettings()
        if lookup_mode is not None and lookup_mode not in self._MODES:
            raise ValueError(
                f"unknown lookup_mode {lookup_mode!r}; "
                f"expected one of {sorted(self._MODES)} or None"
            )
        self.lookup_mode = lookup_mode
        if lookup_mode is None:
            self.name = "related_entities"
        else:
            self.name = f"related_entities:{lookup_mode}"

    def contribute(
        self,
        request: Any,
        context: dict[str, Any],
        current: DoD,
    ) -> SourceContribution:
        if self.store is None:
            return SourceContribution(source_name=self.name)

        entity_id = context.get(CONTEXT_KEY_ENTITY_ID)
        if not entity_id:
            return SourceContribution(source_name=self.name)
        if not self.store.exists(entity_id):
            return SourceContribution(
                source_name=self.name,
                evidence={"entity_id": entity_id, "found": False},
            )

        focal = self.store.read(entity_id)

        if self.lookup_mode == self.MODE_PREFIX:
            related_ids = self._prefix_siblings(entity_id)
        elif self.lookup_mode == self.MODE_TAGS:
            related_ids = self._tag_siblings(entity_id, focal)
        else:
            # lookup_mode is None: union of both, dedup by id.
            related_ids = self._prefix_siblings(entity_id)
            for rid in self._tag_siblings(entity_id, focal):
                if rid not in related_ids:
                    related_ids.append(rid)

        related_ids = related_ids[: self.settings.max_related]

        if not related_ids:
            return SourceContribution(
                source_name=self.name,
                evidence={
                    "entity_id": entity_id,
                    "lookup_mode": self.lookup_mode,
                    "related_found": 0,
                },
            )

        existing = {c.name for c in current.criteria}
        criteria, contributing_ids = self._collect_criteria(
            related_ids, existing
        )

        if not criteria:
            return SourceContribution(
                source_name=self.name,
                evidence={
                    "entity_id": entity_id,
                    "lookup_mode": self.lookup_mode,
                    "related_found": len(related_ids),
                    "related_ids": related_ids,
                    "criteria_extracted": 0,
                },
            )

        delta = min(
            len(contributing_ids) * self.settings.confidence_per_related,
            self.settings.max_confidence_delta,
        )
        return SourceContribution(
            source_name=self.name,
            criteria=criteria,
            confidence_delta=delta,
            evidence={
                "entity_id": entity_id,
                "lookup_mode": self.lookup_mode,
                "related_found": len(related_ids),
                "related_ids": related_ids,
                "contributing_ids": contributing_ids,
                "criteria_extracted": len(criteria),
            },
        )

    # ---------- prefix-cluster heuristic

    def _prefix_siblings(self, entity_id: str) -> list[str]:
        sep = self.settings.prefix_separator
        if sep not in entity_id:
            return []
        prefix = entity_id.split(sep, 1)[0]
        if not prefix:
            return []
        return [
            other
            for other in self.store.list()
            if other != entity_id
            and sep in other
            and other.split(sep, 1)[0] == prefix
        ]

    # ---------- tag-overlap heuristic

    def _tag_siblings(
        self, entity_id: str, focal
    ) -> list[str]:
        focal_tags = self._tags_of(focal)
        if not focal_tags:
            return []
        min_overlap = self.settings.tags_min_overlap
        out: list[str] = []
        for other_id in self.store.list():
            if other_id == entity_id:
                continue
            other = self.store.read(other_id)
            other_tags = self._tags_of(other)
            if not other_tags:
                continue
            if len(focal_tags & other_tags) >= min_overlap:
                out.append(other_id)
        return out

    def _tags_of(self, entity) -> set[str]:
        raw = entity.frontmatter.get(self.settings.tags_frontmatter_key)
        if not isinstance(raw, list):
            return set()
        return {str(t) for t in raw if isinstance(t, (str, int))}

    # ---------- criteria extraction

    def _collect_criteria(
        self,
        related_ids: list[str],
        existing: set[str],
    ) -> tuple[list[Criterion], list[str]]:
        seen: set[str] = set()
        out: list[Criterion] = []
        contributing: list[str] = []
        factor = self.settings.cross_entity_weight_factor

        for rid in related_ids:
            if not self.store.exists(rid):
                continue
            sibling = self.store.read(rid)
            raw = sibling.frontmatter.get(FRONTMATTER_KEY)
            if not isinstance(raw, dict):
                continue
            raw_criteria = raw.get("criteria")
            if not isinstance(raw_criteria, list):
                continue
            contributed_this_round = False
            for raw_c in raw_criteria:
                if not isinstance(raw_c, dict):
                    continue
                name = raw_c.get("name")
                expected = raw_c.get("expected")
                if not name or expected is None:
                    continue
                if name in existing or name in seen:
                    continue
                weight = float(raw_c.get("weight", 1.0)) * factor
                criterion = Criterion(
                    name=str(name),
                    expected=expected,
                    weight=weight,
                )
                # source label set on the criterion is informational;
                # the engine overrides with the contribution's
                # source_name on merge. We still set it for in-test
                # inspection of raw SourceContribution objects.
                criterion = replace(criterion, source=self.name)
                seen.add(name)
                out.append(criterion)
                contributed_this_round = True
            if contributed_this_round:
                contributing.append(rid)

        return out, contributing
