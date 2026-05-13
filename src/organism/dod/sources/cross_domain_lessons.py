"""Cross-domain lessons source — the Dreaming-equivalent.

The default ``LessonsSource`` pulls lessons scoped to the *current*
``kind``. ``CrossDomainLessonsSource`` complements it by pulling
lessons recorded under *other* kinds when ``context_pattern`` overlap
suggests the underlying pattern is shared.

This is organism-core's analogue of Anthropic's "Dreaming" feature
(Claude Managed Agents, research preview, May 2026), which
consolidates patterns across past sessions of multiple agents. Where
Anthropic's Dreaming runs a separate background pipeline, the source
here pulls inline at DoD-derive time — same intent (knowledge leaks
across kinds when patterns are shared), different mechanism.

Cross-kind transfer is **deliberately conservative**:

- Requires explicit ``match_keys`` (e.g. ``["domain", "subtype"]``).
  An empty list matches no lessons — opt-in, not opt-out.
- All match keys must be present and equal on both sides. Missing
  key on either side fails the match.
- Re-injected criteria carry a reduced weight
  (``cross_kind_weight_factor``, default ``0.3``) compared to
  same-kind lessons.
- Confidence contribution is low by default (``0.05``) so the source
  rarely triggers an engine early-exit on its own.

The trust model: same-kind lessons (``LessonsSource``) are primary
signal; cross-kind lessons (this source) are *secondary hints* worth
considering but never decisive.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from organism.dod.types import Criterion, DoD, SourceContribution
from organism.lessons.aggregator import LessonsAggregator

CONTEXT_KEY_KIND = "kind"
CROSS_KIND_CRITERION_SOURCE = "cross_domain_lesson"


class CrossDomainLessonsSource:
    """Contributes criteria_hint from lessons recorded under other kinds.

    Hard requirements:
    - ``match_keys`` must be non-empty (caller intent: which context
      dimensions define a "domain family"?). Empty list = no transfer.
    - ``context[CONTEXT_KEY_KIND]`` must be set on the request; the
      source uses it as ``exclude_kind`` to avoid self-injection.
    """

    name = "cross_domain_lessons"

    def __init__(
        self,
        aggregator: LessonsAggregator | None = None,
        *,
        match_keys: list[str] | None = None,
        confidence_delta: float = 0.05,
        cross_kind_weight_factor: float = 0.3,
        max_results: int | None = None,
    ) -> None:
        if not 0.0 <= confidence_delta <= 1.0:
            raise ValueError(
                "confidence_delta must be in [0, 1], "
                f"got {confidence_delta}"
            )
        if not 0.0 <= cross_kind_weight_factor <= 1.0:
            raise ValueError(
                "cross_kind_weight_factor must be in [0, 1], "
                f"got {cross_kind_weight_factor}"
            )
        if max_results is not None and max_results <= 0:
            raise ValueError(
                f"max_results must be > 0 or None, got {max_results}"
            )
        self.aggregator = aggregator
        self.match_keys = list(match_keys or [])
        self.confidence_delta = confidence_delta
        self.cross_kind_weight_factor = cross_kind_weight_factor
        self.max_results = max_results

    def contribute(
        self,
        request: Any,
        context: dict[str, Any],
        current: DoD,
    ) -> SourceContribution:
        if self.aggregator is None or not self.match_keys:
            return SourceContribution(
                source_name=self.name,
                evidence={"reason": "no aggregator or empty match_keys"},
            )

        current_kind = context.get(CONTEXT_KEY_KIND)
        if not current_kind:
            return SourceContribution(
                source_name=self.name,
                evidence={"reason": "no kind in context"},
            )

        lessons = self.aggregator.query_cross_kind(
            exclude_kind=current_kind,
            context=context,
            match_keys=self.match_keys,
            max_results=self.max_results,
        )

        if not lessons:
            return SourceContribution(
                source_name=self.name,
                evidence={
                    "queried_match_keys": list(self.match_keys),
                    "lessons_found": 0,
                },
            )

        existing = {c.name for c in current.criteria}
        criteria: list[Criterion] = []
        seen: set[str] = set()
        lesson_ids: list[str] = []
        contributing_kinds: set[str] = set()

        for lesson in lessons:
            lesson_ids.append(lesson.id)
            contributing_kinds.add(lesson.kind)
            for hint in lesson.criteria_hint:
                if hint.name in existing or hint.name in seen:
                    continue
                seen.add(hint.name)
                criteria.append(
                    replace(
                        hint,
                        weight=hint.weight * self.cross_kind_weight_factor,
                        source=CROSS_KIND_CRITERION_SOURCE,
                    )
                )

        return SourceContribution(
            source_name=self.name,
            criteria=criteria,
            confidence_delta=(
                self.confidence_delta if criteria else 0.0
            ),
            evidence={
                "queried_match_keys": list(self.match_keys),
                "lessons_found": len(lessons),
                "contributing_kinds": sorted(contributing_kinds),
                "lesson_ids": lesson_ids,
            },
        )
