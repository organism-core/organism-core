from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from organism.dod.types import DoD, SourceContribution


@runtime_checkable
class DoDSource(Protocol):
    name: str

    def contribute(
        self,
        request: Any,
        context: dict[str, Any],
        current: DoD,
    ) -> SourceContribution: ...
