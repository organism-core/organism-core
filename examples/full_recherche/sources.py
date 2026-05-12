"""Consumer-facing source implementations for the full-recherche demo.

The Skelett ships ``RelatedEntitiesSource``, ``VectorSearchSource``, and
``DomainPatternSource`` as empty stubs — they are plug-points where
consumers wire their own data sources into the M5 hierarchy. This module
shows three minimal, generic implementations that a consumer might write
to fill those slots: a store-scan, an in-memory vector mock, and a
pattern registry. They are not intended for production — they are
documentation by code.
"""

from __future__ import annotations

from typing import Any

from organism.dod.types import Criterion, DoD, SourceContribution
from organism.memory import EntityStore


class RelatedEntitiesScanSource:
    """Scans the entity store for entities sharing context-keys with the
    current request, and contributes their criteria — deduplicated against
    what is already in the DoD.

    Skips the request's own entity (avoids contributing the entity to
    itself, which the EntityFrontmatterSource has already done).
    """

    name = "related_entities"

    def __init__(
        self,
        store: EntityStore,
        match_keys: list[str],
        confidence_delta: float = 0.2,
    ) -> None:
        self.store = store
        self.match_keys = list(match_keys)
        self.confidence_delta = confidence_delta

    def contribute(
        self,
        request: Any,
        context: dict[str, Any],
        current: DoD,
    ) -> SourceContribution:
        own_id = context.get("entity_id")
        matched_ids: list[str] = []
        candidate_specs: list[dict[str, Any]] = []

        for entity_id in self.store.list():
            if entity_id == own_id:
                continue
            entity = self.store.read(entity_id)
            fm = entity.frontmatter
            if not all(
                fm.get(k) == context.get(k) for k in self.match_keys
            ):
                continue
            matched_ids.append(entity_id)
            dod_block = fm.get("dod") or {}
            for raw in dod_block.get("criteria", []) or []:
                candidate_specs.append(raw)

        existing = {c.name for c in current.criteria}
        seen: set[str] = set()
        criteria: list[Criterion] = []
        for raw in candidate_specs:
            name = raw.get("name")
            if not name or name in existing or name in seen:
                continue
            seen.add(name)
            criteria.append(
                Criterion(
                    name=name,
                    expected=raw["expected"],
                    weight=float(raw.get("weight", 0.5)),
                )
            )

        return SourceContribution(
            source_name=self.name,
            criteria=criteria,
            confidence_delta=self.confidence_delta if criteria else 0.0,
            evidence={
                "match_keys": list(self.match_keys),
                "matched_entities": matched_ids,
            },
        )


class StaticVectorSearchSource:
    """Synthetic in-memory vector mock, indexed by ``kind``.

    Consumers replace this with a real Chroma/Pinecone/Weaviate-backed
    source. The interface stays the same: contribute criteria for the
    current ``kind``.
    """

    name = "vector_search"

    def __init__(
        self,
        index: dict[str, list[dict[str, Any]]],
        confidence_delta: float = 0.1,
    ) -> None:
        self.index = index
        self.confidence_delta = confidence_delta

    def contribute(
        self,
        request: Any,
        context: dict[str, Any],
        current: DoD,
    ) -> SourceContribution:
        kind = context.get("kind") or ""
        specs = self.index.get(kind, [])
        existing = {c.name for c in current.criteria}
        criteria = [
            Criterion(
                name=spec["name"],
                expected=spec["expected"],
                weight=float(spec.get("weight", 0.4)),
            )
            for spec in specs
            if spec["name"] not in existing
        ]
        return SourceContribution(
            source_name=self.name,
            criteria=criteria,
            confidence_delta=self.confidence_delta if criteria else 0.0,
            evidence={"queried_kind": kind, "results": len(criteria)},
        )


class PatternRegistrySource:
    """In-memory pattern registry keyed by a single context discriminator.

    Consumers replace with an actual registry — file-tree, DB, or rule
    engine. The interface stays the same: contribute criteria for the
    pattern matching ``context[pattern_key]``.
    """

    name = "domain_pattern"

    def __init__(
        self,
        patterns: dict[str, list[dict[str, Any]]],
        pattern_key: str,
        confidence_delta: float = 0.1,
    ) -> None:
        self.patterns = patterns
        self.pattern_key = pattern_key
        self.confidence_delta = confidence_delta

    def contribute(
        self,
        request: Any,
        context: dict[str, Any],
        current: DoD,
    ) -> SourceContribution:
        key = context.get(self.pattern_key) or ""
        specs = self.patterns.get(key, [])
        existing = {c.name for c in current.criteria}
        criteria = [
            Criterion(
                name=spec["name"],
                expected=spec["expected"],
                weight=float(spec.get("weight", 0.3)),
            )
            for spec in specs
            if spec["name"] not in existing
        ]
        return SourceContribution(
            source_name=self.name,
            criteria=criteria,
            confidence_delta=self.confidence_delta if criteria else 0.0,
            evidence={
                "pattern_key": self.pattern_key,
                "key_value": key,
                "results": len(criteria),
            },
        )
