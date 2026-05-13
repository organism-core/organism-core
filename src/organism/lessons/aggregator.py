from __future__ import annotations

import math
import uuid
from datetime import datetime, timedelta, timezone
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
        # Per-lesson last-used tracking for the observability sensor.
        # In-memory only — process restart resets. This is a sensor for
        # detecting lesson-pile-noise patterns over hours/days, not a
        # persistent audit log.
        self._last_used: dict[str, datetime] = {}

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
        # Stable order: timestamp desc, then id desc as tie-breaker —
        # absorbs Windows 15ms clock-resolution quirks when lessons are
        # written in tight succession.
        matching.sort(key=lambda l: (l.recorded_at, l.id), reverse=True)
        result = matching[:cap]
        self._mark_used(result)
        return result

    def query_cross_kind(
        self,
        *,
        exclude_kind: str,
        context: dict[str, Any],
        match_keys: list[str],
        max_results: int | None = None,
    ) -> list[Lesson]:
        """Query lessons recorded under kinds OTHER than ``exclude_kind``.

        A lesson matches when, for every key in ``match_keys``, both
        the lesson's ``context_pattern`` and the supplied ``context``
        have the same non-None value. An empty ``match_keys`` list
        matches no lessons (cross-kind transfer must be deliberate).

        Returns newest-first, capped at ``max_results`` (default
        ``settings.query_max_results``).
        """
        if not match_keys:
            return []
        cap = max_results or self.settings.query_max_results
        matching: list[Lesson] = []
        for lesson in self.store.list():
            if lesson.kind == exclude_kind:
                continue
            if not _matches_keys(
                lesson.context_pattern, context, match_keys
            ):
                continue
            matching.append(lesson)
        # Stable order: timestamp desc, then id desc as tie-breaker —
        # absorbs Windows 15ms clock-resolution quirks when lessons are
        # written in tight succession.
        matching.sort(key=lambda l: (l.recorded_at, l.id), reverse=True)
        result = matching[:cap]
        self._mark_used(result)
        return result

    def _mark_used(self, lessons: list[Lesson]) -> None:
        now = datetime.now(timezone.utc)
        for lesson in lessons:
            self._last_used[lesson.id] = now

    def lesson_last_used(self, lesson_id: str) -> datetime | None:
        """Last time a query returned this lesson, or None if never
        queried since process start. In-memory only."""
        return self._last_used.get(lesson_id)

    def usage_stats(
        self,
        *,
        kind: str | None = None,
        recent_window_seconds: int = 604800,
    ) -> dict[str, Any]:
        """Aggregate lesson-pile observability metrics.

        Detects the lesson-pile-noise pattern: lessons accumulating
        over time without being picked up by queries (the failure mode
        a future distillation worker would address). Two signals:

        - ``age_days_p95``: 95th percentile age in days. Grows when
          old lessons never get replaced.
        - ``recent_use_ratio``: fraction of lessons used in the last
          ``recent_window_seconds`` (default 7 days). Drops toward 0
          when accumulated lessons aren't being picked up — the noise
          signal.

        Watch both: high ``total`` + high ``age_days_p95`` + low
        ``recent_use_ratio`` = pile-up. Consider distillation.

        Returns a dict (not a typed dataclass) to keep the sensor
        cheap to evolve. Always includes:
        - ``total``: int
        - ``recent_window_seconds``: int (echo of the input)
        - ``recent_use_ratio``: float in [0, 1]; 0.0 when total == 0
        - ``age_days_p95``: float | None; None when total == 0
        - ``never_used_count``: int (lessons not in _last_used)
        """
        lessons = self.store.list(kind=kind)
        if not lessons:
            return {
                "total": 0,
                "recent_window_seconds": recent_window_seconds,
                "recent_use_ratio": 0.0,
                "age_days_p95": None,
                "never_used_count": 0,
            }

        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(seconds=recent_window_seconds)

        recent_used = 0
        never_used = 0
        for lesson in lessons:
            last = self._last_used.get(lesson.id)
            if last is None:
                never_used += 1
            elif last >= cutoff:
                recent_used += 1

        ages_days = sorted(
            (now - lesson.recorded_at).total_seconds() / 86400.0
            for lesson in lessons
        )
        # P95: ceiling-based index. For a single element, p95 == that
        # element's age. For larger N, index points to the value such
        # that 95% of values are <= it.
        idx = max(0, math.ceil(0.95 * len(ages_days)) - 1)
        p95 = ages_days[idx]

        return {
            "total": len(lessons),
            "recent_window_seconds": recent_window_seconds,
            "recent_use_ratio": recent_used / len(lessons),
            "age_days_p95": p95,
            "never_used_count": never_used,
        }


def _matches_context(lesson: Lesson, context: dict[str, Any]) -> bool:
    return all(
        context.get(key) == value
        for key, value in lesson.context_pattern.items()
    )


def _matches_keys(
    lesson_pattern: dict[str, Any],
    request_context: dict[str, Any],
    match_keys: list[str],
) -> bool:
    """For every key in ``match_keys``, both the lesson's
    ``context_pattern`` and the request ``context`` must have the same
    non-None value. A missing key on either side fails the match — we
    never silently transfer lessons across kinds when the discriminator
    is absent."""
    for key in match_keys:
        lesson_value = lesson_pattern.get(key)
        context_value = request_context.get(key)
        if lesson_value is None or context_value is None:
            return False
        if lesson_value != context_value:
            return False
    return True
