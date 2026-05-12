from __future__ import annotations

from typing import Any

from organism.dod.settings import EntityFrontmatterSettings
from organism.dod.types import Criterion, DoD, SourceContribution
from organism.memory import EntityStore

CONTEXT_KEY_ENTITY_ID = "entity_id"
FRONTMATTER_KEY = "dod"


class EntityFrontmatterSource:
    name = "entity_frontmatter"

    def __init__(
        self,
        store: EntityStore,
        settings: EntityFrontmatterSettings | None = None,
    ) -> None:
        self.store = store
        self.settings = settings or EntityFrontmatterSettings()

    def contribute(
        self,
        request: Any,
        context: dict[str, Any],
        current: DoD,
    ) -> SourceContribution:
        entity_id = context.get(CONTEXT_KEY_ENTITY_ID)
        if not entity_id:
            return SourceContribution(source_name=self.name)

        if not self.store.exists(entity_id):
            return SourceContribution(
                source_name=self.name,
                evidence={"entity_id": entity_id, "found": False},
            )

        entity = self.store.read(entity_id)
        raw_dod = entity.frontmatter.get(FRONTMATTER_KEY)
        if raw_dod is not None and not isinstance(raw_dod, dict):
            raise ValueError(
                f"frontmatter '{FRONTMATTER_KEY}' must be a mapping, "
                f"got {type(raw_dod).__name__}"
            )
        dod_block: dict[str, Any] = raw_dod or {}

        raw_criteria = dod_block.get("criteria")
        if raw_criteria is not None and not isinstance(raw_criteria, list):
            raise ValueError(
                f"frontmatter '{FRONTMATTER_KEY}.criteria' must be a list, "
                f"got {type(raw_criteria).__name__}"
            )
        criteria_raw: list[Any] = raw_criteria or []

        criteria = [_parse_criterion(c) for c in criteria_raw]

        evidence: dict[str, Any] = {
            "entity_id": entity_id,
            "found": True,
            "criteria_count": len(criteria),
        }
        confidence_delta = (
            self.settings.confidence_when_loaded if criteria else 0.0
        )

        return SourceContribution(
            source_name=self.name,
            criteria=criteria,
            confidence_delta=confidence_delta,
            evidence=evidence,
        )


def _parse_criterion(raw: Any) -> Criterion:
    if not isinstance(raw, dict):
        raise ValueError(
            f"frontmatter dod.criteria entry must be a mapping, "
            f"got {type(raw).__name__}"
        )
    if "name" not in raw:
        raise ValueError(
            "frontmatter dod.criteria entry missing required 'name'"
        )
    if "expected" not in raw:
        raise ValueError(
            f"frontmatter dod.criteria entry '{raw['name']}' missing "
            "required 'expected'"
        )
    return Criterion(
        name=raw["name"],
        expected=raw["expected"],
        weight=float(raw.get("weight", 1.0)),
    )
