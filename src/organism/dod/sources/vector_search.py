from __future__ import annotations

from typing import Any

from organism.dod.types import DoD, SourceContribution


class VectorSearchSource:
    name = "vector_search"

    def __init__(self, client: Any = None) -> None:
        self.client = client

    def contribute(
        self,
        request: Any,
        context: dict[str, Any],
        current: DoD,
    ) -> SourceContribution:
        return SourceContribution(source_name=self.name)
