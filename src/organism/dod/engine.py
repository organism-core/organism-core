from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from typing import Any

from organism.dod.settings import DoDEngineSettings
from organism.dod.source import DoDSource
from organism.dod.types import DoD, SourceContribution


class DoDEngine:
    """Star-pattern DoD-Recherche engine.

    Default (`parallel=False`): iterates the configured sources
    sequentially. Each source sees the wachsende DoD (`current`) and
    can decide based on what's already in it (dedup itself, suppress
    clarifications, etc.). Engine stops early when
    ``dod.confidence >= settings.threshold`` AND
    ``dod.clarification_needed`` is empty.

    Optional (`parallel=True`): dispatches all sources concurrently
    via a ``ThreadPoolExecutor``. Each source sees a fresh empty DoD
    (``current = DoD()``), so source-level dedup against ``current``
    is a no-op; the engine performs name-keyed deduplication post-hoc.
    The merge order is still deterministic — sources are merged in
    the order they were passed to the constructor, regardless of
    completion order.

    When to use ``parallel=True``: production configurations where
    sources make real I/O calls (vector DB, pattern registry, remote
    API) and per-source latencies add up under the sequential model.
    Latency becomes ``max(source_latencies)`` instead of
    ``sum(source_latencies)``.

    Trade-offs of ``parallel=True``:
    - **Early-exit is disabled.** All sources run regardless of how
      quickly confidence accumulates. Pay the full source cost every
      time.
    - **Source-level dedup is suppressed.** Sources that filtered
      against ``current.criteria`` see an empty DoD and emit their
      full contribution; the engine dedupes on the way in.
    - **Sources must be thread-safe.** All built-in sources are
      read-only against their backing stores — safe. Custom sources
      must hold no mutable per-call state outside the ``contribute``
      method.
    """

    def __init__(
        self,
        sources: list[DoDSource],
        settings: DoDEngineSettings | None = None,
        *,
        parallel: bool = False,
        max_workers: int | None = None,
    ) -> None:
        self.sources: list[DoDSource] = list(sources)
        self.settings = settings or DoDEngineSettings()
        self.parallel = parallel
        self.max_workers = max_workers

    def derive(
        self,
        request: Any,
        context: dict[str, Any] | None = None,
    ) -> DoD:
        ctx: dict[str, Any] = dict(context or {})
        if self.parallel:
            return self._derive_parallel(request, ctx)
        return self._derive_sequential(request, ctx)

    def _derive_sequential(
        self, request: Any, ctx: dict[str, Any]
    ) -> DoD:
        dod = DoD()
        for source in self.sources:
            contribution = source.contribute(request, ctx, dod)
            self._merge(dod, contribution)
            if self._satisfied(dod):
                break
        return dod

    def _derive_parallel(
        self, request: Any, ctx: dict[str, Any]
    ) -> DoD:
        if not self.sources:
            return DoD()
        empty_view = DoD()
        contributions_by_name: dict[str, SourceContribution] = {}
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_source = {
                executor.submit(
                    source.contribute, request, ctx, empty_view
                ): source
                for source in self.sources
            }
            for future in as_completed(future_to_source):
                source = future_to_source[future]
                try:
                    contribution = future.result()
                except Exception as exc:
                    contribution = SourceContribution(
                        source_name=source.name,
                        evidence={
                            "error": f"{type(exc).__name__}: {exc}",
                        },
                    )
                contributions_by_name[source.name] = contribution

        # Merge in the original sources-order so the resulting DoD is
        # deterministic regardless of completion order. Engine
        # performs name-keyed dedup since sources couldn't.
        dod = DoD()
        existing_names: set[str] = set()
        for source in self.sources:
            contribution = contributions_by_name.get(source.name)
            if contribution is None:
                continue
            self._merge_with_dedup(dod, contribution, existing_names)
        return dod

    def _merge(
        self, dod: DoD, contribution: SourceContribution
    ) -> None:
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

    def _merge_with_dedup(
        self,
        dod: DoD,
        contribution: SourceContribution,
        existing_names: set[str],
    ) -> None:
        """Parallel-mode merge: dedupe by criterion.name against the
        running DoD because sources saw an empty view and could not
        dedupe themselves."""
        contributed_names: list[str] = []
        for criterion in contribution.criteria:
            if criterion.name in existing_names:
                continue
            stamped = replace(criterion, source=contribution.source_name)
            dod.criteria.append(stamped)
            existing_names.add(stamped.name)
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
