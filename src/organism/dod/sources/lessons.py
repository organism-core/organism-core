from __future__ import annotations

from typing import Any

from organism.dod.types import DoD, SourceContribution
from organism.lessons.aggregator import LessonsAggregator
from organism.lessons.settings import LessonsSourceSettings

CONTEXT_KEY_KIND = "kind"


class LessonsSource:
    name = "lessons"

    def __init__(
        self,
        aggregator: LessonsAggregator | None = None,
        settings: LessonsSourceSettings | None = None,
    ) -> None:
        self.aggregator = aggregator
        self.settings = settings or LessonsSourceSettings()

    def contribute(
        self,
        request: Any,
        context: dict[str, Any],
        current: DoD,
    ) -> SourceContribution:
        if self.aggregator is None:
            return SourceContribution(source_name=self.name)

        kind = context.get(CONTEXT_KEY_KIND)
        if not kind:
            return SourceContribution(source_name=self.name)

        lessons = self.aggregator.query_for_request(kind, context)
        if not lessons:
            return SourceContribution(
                source_name=self.name,
                evidence={"queried_kind": kind, "lessons_found": 0},
            )

        criteria = []
        total_confidence = 0.0
        for lesson in lessons:
            criteria.extend(lesson.criteria_hint)
            total_confidence += lesson.confidence_delta

        capped_confidence = min(
            total_confidence, self.settings.max_confidence_delta
        )

        return SourceContribution(
            source_name=self.name,
            criteria=criteria,
            confidence_delta=capped_confidence,
            evidence={
                "queried_kind": kind,
                "lessons_found": len(lessons),
                "lesson_ids": [lesson.id for lesson in lessons],
            },
        )
