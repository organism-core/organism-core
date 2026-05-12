from __future__ import annotations

from typing import Any

from organism.dod.types import DoD, SourceContribution
from organism.memory import EntityStore


class RelatedEntitiesSource:
    name = "related_entities"

    def __init__(self, store: EntityStore | None = None) -> None:
        self.store = store

    def contribute(
        self,
        request: Any,
        context: dict[str, Any],
        current: DoD,
    ) -> SourceContribution:
        return SourceContribution(source_name=self.name)
