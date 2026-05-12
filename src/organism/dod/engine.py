from __future__ import annotations

from dataclasses import replace
from typing import Any

from organism.dod.settings import DoDEngineSettings
from organism.dod.source import DoDSource
from organism.dod.types import DoD, SourceContribution


class DoDEngine:
    def __init__(
        self,
        sources: list[DoDSource],
        settings: DoDEngineSettings | None = None,
    ) -> None:
        self.sources: list[DoDSource] = list(sources)
        self.settings = settings or DoDEngineSettings()

    def derive(
        self,
        request: Any,
        context: dict[str, Any] | None = None,
    ) -> DoD:
        ctx: dict[str, Any] = dict(context or {})
        dod = DoD()
        for source in self.sources:
            contribution = source.contribute(request, ctx, dod)
            self._merge(dod, contribution)
            if self._satisfied(dod):
                break
        return dod

    def _merge(self, dod: DoD, contribution: SourceContribution) -> None:
        contributed_names: list[str] = []
        for criterion in contribution.criteria:
            stamped = replace(criterion, source=contribution.source_name)
            dod.criteria.append(stamped)
            contributed_names.append(stamped.name)

        dod.clarification_needed.extend(contribution.clarifications)
        dod.confidence = max(
            0.0, min(1.0, dod.confidence + contribution.confidence_delta)
        )

        if contributed_names or contribution.evidence:
            dod._provenance.setdefault(contribution.source_name, [])
            dod._provenance[contribution.source_name].extend(contributed_names)

    def _satisfied(self, dod: DoD) -> bool:
        return (
            dod.confidence >= self.settings.threshold
            and not dod.clarification_needed
        )
