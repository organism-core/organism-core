from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from organism.dod.types import Criterion
from organism.lessons.settings import LessonsAggregatorSettings
from organism.lessons.store import LessonsStore
from organism.lessons.types import Lesson
from organism.provenance import Provenance

if TYPE_CHECKING:
    from organism.observability.event_bus import EventBus

EVENT_LESSON_RECORDED = "lesson_recorded"


class LessonsAggregator:
    def __init__(
        self,
        store: LessonsStore,
        settings: LessonsAggregatorSettings | None = None,
        event_bus: "EventBus | None" = None,
    ) -> None:
        self.store = store
        self.settings = settings or LessonsAggregatorSettings()
        self.event_bus = event_bus

    def record_lesson(
        self,
        *,
        kind: str,
        observation: str,
        criteria_hint: list[Criterion] | None = None,
        confidence_delta: float = 0.0,
        context_pattern: dict[str, Any] | None = None,
        provenance: Provenance | None = None,
    ) -> Lesson:
        now = datetime.now(timezone.utc)
        lesson = Lesson(
            id=str(uuid.uuid4()),
            kind=kind,
            observation=observation,
            provenance=provenance or Provenance(author="system", timestamp=now),
            recorded_at=now,
            context_pattern=dict(context_pattern or {}),
            criteria_hint=list(criteria_hint or []),
            confidence_delta=confidence_delta,
        )
        self.store.write(lesson)
        self._publish_recorded(lesson)
        return lesson

    def _publish_recorded(self, lesson: Lesson) -> None:
        if self.event_bus is None:
            return
        from organism.observability.event_bus import Event

        self.event_bus.publish(
            Event.now(
                type=EVENT_LESSON_RECORDED,
                payload={
                    "lesson_id": lesson.id,
                    "kind": lesson.kind,
                    "observation": lesson.observation,
                },
                provenance=Provenance.now(
                    author="lessons_aggregator",
                    source=EVENT_LESSON_RECORDED,
                ),
            )
        )

    def query_for_request(
        self,
        kind: str,
        context: dict[str, Any],
        max_results: int | None = None,
    ) -> list[Lesson]:
        cap = max_results or self.settings.query_max_results
        all_for_kind = self.store.list(kind=kind)
        matching = [
            lesson
            for lesson in all_for_kind
            if _matches_context(lesson, context)
        ]
        matching.sort(key=lambda l: l.recorded_at, reverse=True)
        return matching[:cap]


def _matches_context(lesson: Lesson, context: dict[str, Any]) -> bool:
    return all(
        context.get(key) == value
        for key, value in lesson.context_pattern.items()
    )
