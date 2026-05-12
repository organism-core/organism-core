from __future__ import annotations

from typing import Any

from organism.dod.types import DoD, SourceContribution


class DomainPatternSource:
    name = "domain_pattern"

    def __init__(self, registry: Any = None) -> None:
        self.registry = registry

    def contribute(
        self,
        request: Any,
        context: dict[str, Any],
        current: DoD,
    ) -> SourceContribution:
        return SourceContribution(source_name=self.name)
