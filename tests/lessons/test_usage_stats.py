"""Tests for LessonsAggregator's lesson-pile observability sensor.

`usage_stats()` reports two signals that together detect lessons
accumulating without being used:

- ``age_days_p95``: 95th percentile age in days; grows when old
  lessons aren't replaced.
- ``recent_use_ratio``: fraction of lessons used in the configurable
  recent window; falls toward 0 when piling-up lessons aren't picked
  up by queries.

The `_last_used` tracking is in-memory only (process restart resets)
— this is a sensor, not a persistent audit log.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from organism.dod.types import Criterion
from organism.lessons import LessonsAggregator, LessonsStore


def _agg(tmp_path: Path) -> LessonsAggregator:
    return LessonsAggregator(store=LessonsStore(tmp_path / "lessons"))


def _seed(
    agg: LessonsAggregator,
    *,
    kind: str = "k",
    name: str = "c",
    context_pattern: dict | None = None,
):
    return agg.record_lesson(
        kind=kind,
        observation=f"lesson for {name}",
        criteria_hint=[Criterion(name=name, expected=True)],
        context_pattern=context_pattern or {},
    )


# ---------- Empty store


def test_usage_stats_on_empty_store_returns_zeros():
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        agg = LessonsAggregator(store=LessonsStore(Path(tmp)))
        stats = agg.usage_stats(kind="k")
        assert stats["total"] == 0
        assert stats["recent_use_ratio"] == 0.0
        assert stats["age_days_p95"] is None
        assert stats["never_used_count"] == 0


# ---------- Total + age


def test_usage_stats_total_counts_lessons(tmp_path: Path):
    agg = _agg(tmp_path)
    for i in range(5):
        _seed(agg, name=f"c{i}")
    stats = agg.usage_stats(kind="k")
    assert stats["total"] == 5


def test_usage_stats_total_filters_by_kind(tmp_path: Path):
    agg = _agg(tmp_path)
    _seed(agg, kind="k_a", name="c1")
    _seed(agg, kind="k_a", name="c2")
    _seed(agg, kind="k_b", name="c3")
    assert agg.usage_stats(kind="k_a")["total"] == 2
    assert agg.usage_stats(kind="k_b")["total"] == 1


def test_usage_stats_age_p95_for_freshly_recorded_is_near_zero(tmp_path: Path):
    agg = _agg(tmp_path)
    _seed(agg)
    stats = agg.usage_stats(kind="k")
    assert stats["age_days_p95"] < 0.01  # under 14 minutes


# ---------- last_used tracking


def test_lesson_never_used_returns_none_for_last_used(tmp_path: Path):
    agg = _agg(tmp_path)
    lesson = _seed(agg)
    assert agg.lesson_last_used(lesson.id) is None


def test_query_for_request_marks_returned_lessons_as_used(tmp_path: Path):
    agg = _agg(tmp_path)
    lesson = _seed(agg, context_pattern={"domain": "alpha"})
    before = datetime.now(timezone.utc)
    agg.query_for_request(kind="k", context={"domain": "alpha"})
    after = datetime.now(timezone.utc)

    last_used = agg.lesson_last_used(lesson.id)
    assert last_used is not None
    assert before <= last_used <= after


def test_query_cross_kind_marks_returned_lessons_as_used(tmp_path: Path):
    agg = _agg(tmp_path)
    lesson = _seed(
        agg, kind="other_kind", context_pattern={"domain": "alpha"}
    )
    agg.query_cross_kind(
        exclude_kind="current_kind",
        context={"domain": "alpha"},
        match_keys=["domain"],
    )
    assert agg.lesson_last_used(lesson.id) is not None


def test_query_does_not_mark_non_matching_lessons(tmp_path: Path):
    agg = _agg(tmp_path)
    matches = _seed(agg, context_pattern={"domain": "alpha"})
    no_match = _seed(agg, context_pattern={"domain": "beta"})

    agg.query_for_request(kind="k", context={"domain": "alpha"})
    assert agg.lesson_last_used(matches.id) is not None
    assert agg.lesson_last_used(no_match.id) is None


# ---------- Recent-use-ratio


def test_recent_use_ratio_zero_when_no_queries(tmp_path: Path):
    agg = _agg(tmp_path)
    _seed(agg, name="c1")
    _seed(agg, name="c2")
    stats = agg.usage_stats(kind="k")
    assert stats["recent_use_ratio"] == 0.0
    assert stats["never_used_count"] == 2


def test_recent_use_ratio_one_when_all_lessons_queried(tmp_path: Path):
    agg = _agg(tmp_path)
    _seed(agg, name="c1")
    _seed(agg, name="c2")
    agg.query_for_request(kind="k", context={})
    stats = agg.usage_stats(kind="k")
    assert stats["recent_use_ratio"] == 1.0
    assert stats["never_used_count"] == 0


def test_recent_use_ratio_partial(tmp_path: Path):
    agg = _agg(tmp_path)
    _seed(agg, name="c1", context_pattern={"d": "alpha"})
    _seed(agg, name="c2", context_pattern={"d": "alpha"})
    _seed(agg, name="c3", context_pattern={"d": "beta"})
    _seed(agg, name="c4", context_pattern={"d": "beta"})
    # Query only alpha-domain: 2 of 4 lessons get marked
    agg.query_for_request(kind="k", context={"d": "alpha"})
    stats = agg.usage_stats(kind="k")
    assert stats["recent_use_ratio"] == 0.5
    assert stats["never_used_count"] == 2


def test_recent_use_ratio_respects_recent_window(tmp_path: Path):
    """A lesson marked used in the past but outside the window should
    NOT count toward recent_use_ratio."""
    agg = _agg(tmp_path)
    lesson = _seed(agg)
    # Manually set the lesson's last-used time to far in the past
    agg._last_used[lesson.id] = datetime.now(timezone.utc) - timedelta(days=30)

    stats_tight = agg.usage_stats(kind="k", recent_window_seconds=86400)  # 1 day
    assert stats_tight["recent_use_ratio"] == 0.0
    assert stats_tight["never_used_count"] == 0  # it WAS used, just stale

    stats_wide = agg.usage_stats(kind="k", recent_window_seconds=86400 * 60)  # 60d
    assert stats_wide["recent_use_ratio"] == 1.0


# ---------- p95 with multiple lessons


def test_age_p95_with_mixed_ages(tmp_path: Path):
    """20 lessons of varying ages — p95 should pick one of the oldest."""
    agg = _agg(tmp_path)
    lessons = []
    for i in range(20):
        lessons.append(_seed(agg, name=f"c{i}"))

    # Manually adjust recorded_at to span 0..19 days old via store re-write
    now = datetime.now(timezone.utc)
    for i, lesson in enumerate(lessons):
        lesson.recorded_at = now - timedelta(days=i)
        agg.store.write(lesson)

    stats = agg.usage_stats(kind="k")
    # p95 of 0..19 days: index ceil(0.95*20)-1 = 18, value at index 18 of
    # sorted ages_days. ages_days = [0, 1, 2, ..., 19], so index 18 = 18.
    assert stats["age_days_p95"] == pytest.approx(18.0, abs=0.01)


def test_age_p95_for_single_lesson_is_that_lesson_age(tmp_path: Path):
    agg = _agg(tmp_path)
    lesson = _seed(agg)
    lesson.recorded_at = datetime.now(timezone.utc) - timedelta(days=3)
    agg.store.write(lesson)
    stats = agg.usage_stats(kind="k")
    assert stats["age_days_p95"] == pytest.approx(3.0, abs=0.01)


# ---------- Pile-up signal


def test_pile_up_signal_high_count_high_age_low_ratio(tmp_path: Path):
    """Simulate the lesson-pile-noise pattern: many old lessons, low
    fraction recently used. This is the configuration the future
    distillation worker would target."""
    agg = _agg(tmp_path)
    now = datetime.now(timezone.utc)
    for i in range(20):
        lesson = _seed(agg, name=f"old_{i}", context_pattern={"d": "alpha"})
        # Age them all to 30+ days
        lesson.recorded_at = now - timedelta(days=30 + i)
        agg.store.write(lesson)

    # Add 2 fresh lessons in a new context-pattern (only these get
    # used by the next query)
    fresh_a = _seed(agg, name="fresh_a", context_pattern={"d": "beta"})
    fresh_b = _seed(agg, name="fresh_b", context_pattern={"d": "beta"})
    agg.query_for_request(kind="k", context={"d": "beta"})

    stats = agg.usage_stats(kind="k", recent_window_seconds=86400)
    # Total 22 lessons, only 2 used recently
    assert stats["total"] == 22
    assert stats["recent_use_ratio"] == pytest.approx(2 / 22, abs=0.01)
    assert stats["age_days_p95"] >= 30.0  # pile-up signal
    assert stats["never_used_count"] == 20


# ---------- recent_window echo


def test_usage_stats_echoes_window_setting(tmp_path: Path):
    agg = _agg(tmp_path)
    _seed(agg)
    stats = agg.usage_stats(kind="k", recent_window_seconds=12345)
    assert stats["recent_window_seconds"] == 12345


# ---------- kind=None aggregates across all kinds


def test_usage_stats_kind_none_aggregates_all(tmp_path: Path):
    agg = _agg(tmp_path)
    _seed(agg, kind="k_a", name="c1")
    _seed(agg, kind="k_a", name="c2")
    _seed(agg, kind="k_b", name="c3")
    stats = agg.usage_stats()  # no kind filter
    assert stats["total"] == 3
