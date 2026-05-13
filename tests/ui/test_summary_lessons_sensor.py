"""Tests for the lesson-pile observability fields on
``EffectorSummaryView``, populated by ``Cockpit.summary()``.

These fields surface the same signal as
``LessonsAggregator.usage_stats()`` but at the dashboard row level —
so a UI consumer can see ``lessons_count`` rising alongside
``lessons_age_days_p95`` rising and ``lessons_recent_use_ratio``
falling, and know to act before the lesson pile becomes noise.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from organism.dod import (
    Criterion,
    DoDEngine,
    DoDValidator,
    SourceContribution,
)
from organism.lessons import LessonsAggregator, LessonsStore
from organism.lifecycle import (
    LifecycleManager,
    LifecycleSettings,
    LifecycleStore,
)
from organism.plan_gate import PlanGate, PlanStore
from organism.ui import Cockpit, CockpitBuilder, CockpitSettings


def _build(tmp_path: Path, settings: CockpitSettings | None = None) -> Cockpit:
    aggregator = LessonsAggregator(store=LessonsStore(tmp_path / "lessons"))
    builder = (
        CockpitBuilder()
        .with_engine(DoDEngine(sources=[]))
        .with_plan_gate(PlanGate(store=PlanStore(tmp_path / "plans")))
        .with_lifecycle(
            LifecycleManager(
                store=LifecycleStore(tmp_path / "lifecycle"),
                settings=LifecycleSettings(initial_stage="proposed"),
            )
        )
        .with_lessons(aggregator)
    )
    if settings is not None:
        builder = builder.with_settings(settings)
    return builder.build()


def _seed_lesson(
    aggregator: LessonsAggregator,
    *,
    kind: str,
    name: str = "c",
    context_pattern: dict | None = None,
):
    return aggregator.record_lesson(
        kind=kind,
        observation=f"obs {name}",
        criteria_hint=[Criterion(name=name, expected=True)],
        context_pattern=context_pattern or {},
    )


# ---------- Defaults populate sensibly


def test_summary_lessons_sensor_defaults_when_no_lessons(tmp_path: Path):
    cockpit = _build(tmp_path)
    cockpit.lifecycle.record_outcome(kind="k1", plan_id=None, score=0.8)
    [row] = cockpit.summary()
    assert row.lessons_count == 0
    assert row.lessons_age_days_p95 is None
    assert row.lessons_recent_use_ratio == 0.0
    assert row.lessons_never_used_count == 0


def test_summary_lessons_sensor_counts_lessons(tmp_path: Path):
    cockpit = _build(tmp_path)
    cockpit.lifecycle.record_outcome(kind="k1", plan_id=None, score=0.8)
    _seed_lesson(cockpit.lessons, kind="k1", name="a")
    _seed_lesson(cockpit.lessons, kind="k1", name="b")
    [row] = cockpit.summary()
    assert row.lessons_count == 2
    assert row.lessons_age_days_p95 is not None
    assert row.lessons_age_days_p95 < 0.01  # very fresh


# ---------- recent_use_ratio reflects queries


def test_summary_recent_use_ratio_rises_after_query(tmp_path: Path):
    cockpit = _build(tmp_path)
    cockpit.lifecycle.record_outcome(kind="k1", plan_id=None, score=0.8)
    _seed_lesson(cockpit.lessons, kind="k1", name="a")
    _seed_lesson(cockpit.lessons, kind="k1", name="b")
    # Before any query
    [row_before] = cockpit.summary()
    assert row_before.lessons_recent_use_ratio == 0.0
    assert row_before.lessons_never_used_count == 2

    # Query both
    cockpit.lessons.query_for_request(kind="k1", context={})
    [row_after] = cockpit.summary()
    assert row_after.lessons_recent_use_ratio == 1.0
    assert row_after.lessons_never_used_count == 0


def test_summary_age_p95_grows_with_old_lessons(tmp_path: Path):
    cockpit = _build(tmp_path)
    cockpit.lifecycle.record_outcome(kind="k1", plan_id=None, score=0.8)
    # Seed 20 lessons spanning 0..19 days old
    now = datetime.now(timezone.utc)
    for i in range(20):
        lesson = _seed_lesson(cockpit.lessons, kind="k1", name=f"c{i}")
        lesson.recorded_at = now - timedelta(days=i)
        cockpit.lessons.store.write(lesson)
    [row] = cockpit.summary()
    assert row.lessons_count == 20
    # p95 of 0..19 days is the 19th-of-20 sorted value: ~18
    assert row.lessons_age_days_p95 == pytest.approx(18.0, abs=0.01)


# ---------- Per-kind isolation


def test_summary_lessons_sensor_is_per_kind(tmp_path: Path):
    cockpit = _build(tmp_path)
    cockpit.lifecycle.record_outcome(kind="k_a", plan_id=None, score=0.8)
    cockpit.lifecycle.record_outcome(kind="k_b", plan_id=None, score=0.8)
    # Lessons under k_a; none under k_b
    _seed_lesson(cockpit.lessons, kind="k_a", name="x")
    _seed_lesson(cockpit.lessons, kind="k_a", name="y")
    rows = {r.kind: r for r in cockpit.summary()}
    assert rows["k_a"].lessons_count == 2
    assert rows["k_b"].lessons_count == 0


# ---------- Settings-driven window


def test_summary_lessons_sensor_window_respects_setting(tmp_path: Path):
    """Lessons used 30 days ago count as recent under a 60-day window
    but not under a 7-day window."""
    cockpit = _build(
        tmp_path,
        settings=CockpitSettings(
            lessons_recent_use_window_seconds=86400 * 60  # 60 days
        ),
    )
    cockpit.lifecycle.record_outcome(kind="k1", plan_id=None, score=0.8)
    lesson = _seed_lesson(cockpit.lessons, kind="k1", name="x")
    # Mark as used 30 days ago
    cockpit.lessons._last_used[lesson.id] = datetime.now(timezone.utc) - timedelta(
        days=30
    )
    [row] = cockpit.summary()
    assert row.lessons_recent_use_ratio == 1.0  # within 60d window


def test_summary_lessons_sensor_window_tight_excludes_old_uses(tmp_path: Path):
    cockpit = _build(
        tmp_path,
        settings=CockpitSettings(
            lessons_recent_use_window_seconds=86400  # 1 day
        ),
    )
    cockpit.lifecycle.record_outcome(kind="k1", plan_id=None, score=0.8)
    lesson = _seed_lesson(cockpit.lessons, kind="k1", name="x")
    cockpit.lessons._last_used[lesson.id] = datetime.now(timezone.utc) - timedelta(
        days=30
    )
    [row] = cockpit.summary()
    assert row.lessons_recent_use_ratio == 0.0


# ---------- Pile-up signal at dashboard level


def test_summary_pile_up_signal_visible(tmp_path: Path):
    """End-to-end: a kind with many old unused lessons surfaces as
    high count + high age + low ratio in the dashboard row."""
    cockpit = _build(tmp_path)
    cockpit.lifecycle.record_outcome(kind="k1", plan_id=None, score=0.8)
    now = datetime.now(timezone.utc)
    # 30 lessons, all >= 14 days old, never used
    for i in range(30):
        lesson = _seed_lesson(cockpit.lessons, kind="k1", name=f"old_{i}")
        lesson.recorded_at = now - timedelta(days=14 + i)
        cockpit.lessons.store.write(lesson)
    [row] = cockpit.summary()
    assert row.lessons_count == 30
    assert row.lessons_age_days_p95 >= 14.0
    assert row.lessons_recent_use_ratio == 0.0
    assert row.lessons_never_used_count == 30


# ---------- Serialization


def test_summary_view_to_dict_includes_sensor_fields(tmp_path: Path):
    cockpit = _build(tmp_path)
    cockpit.lifecycle.record_outcome(kind="k1", plan_id=None, score=0.8)
    _seed_lesson(cockpit.lessons, kind="k1", name="x")
    [row] = cockpit.summary()
    d = row.to_dict()
    assert "lessons_age_days_p95" in d
    assert "lessons_recent_use_ratio" in d
    assert "lessons_never_used_count" in d
