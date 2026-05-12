from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from organism.dod import (
    REVISION_ESCALATE_TO_HUMAN,
    Criterion,
    DoD,
    DoDEngine,
    SourceContribution,
)
from organism.lessons import LessonsAggregator, LessonsStore
from organism.lifecycle import (
    LifecycleManager,
    LifecycleSettings,
    LifecycleStage,
    LifecycleStore,
)
from organism.plan_gate import PlanGate, PlanStore
from organism.ui import Cockpit, CockpitSettings


# ---------- helpers


class _FixedSource:
    name = "fixed"

    def __init__(self, criteria: list[Criterion], confidence: float = 0.9):
        self._criteria = criteria
        self._confidence = confidence

    def contribute(
        self, request: Any, context: dict[str, Any], current: DoD
    ) -> SourceContribution:
        return SourceContribution(
            source_name=self.name,
            criteria=list(self._criteria),
            confidence_delta=self._confidence,
        )


def _build(tmp_path: Path) -> Cockpit:
    engine = DoDEngine(
        sources=[
            _FixedSource(
                criteria=[
                    Criterion(name="x", expected=True, weight=1.0),
                    Criterion(name="y", expected=1, weight=0.5),
                ]
            )
        ]
    )
    plan_gate = PlanGate(store=PlanStore(tmp_path / "plans"))
    lifecycle = LifecycleManager(
        store=LifecycleStore(tmp_path / "lifecycle"),
        settings=LifecycleSettings(
            initial_stage="proposed",
            promote_after_n=3,
            promote_score_threshold=0.9,
            demote_after_n=2,
            demote_score_threshold=0.5,
            window_size=10,
        ),
    )
    lessons = LessonsAggregator(store=LessonsStore(tmp_path / "lessons"))
    return Cockpit(
        engine=engine,
        plan_gate=plan_gate,
        lifecycle=lifecycle,
        lessons=lessons,
    )


# ---------- inspect_dod


def test_inspect_dod_returns_view_with_engine_derived_criteria(tmp_path: Path):
    cockpit = _build(tmp_path)
    view = cockpit.inspect_dod(request="r", context={"kind": "k"})
    assert [c.name for c in view.criteria] == ["x", "y"]  # sorted by weight
    assert view.total_weight == 1.5


# ---------- pending_plans


def test_pending_plans_returns_only_proposed_by_default(tmp_path: Path):
    cockpit = _build(tmp_path)
    p1 = cockpit.plan_gate.propose(
        kind="k1",
        payload={"request": "r1"},
        dod=DoD(),
        proposed_by="ef",
    )
    p2 = cockpit.plan_gate.propose(
        kind="k1",
        payload={"request": "r2"},
        dod=DoD(),
        proposed_by="ef",
    )
    cockpit.plan_gate.reject(p1.id, decided_by="user", reason="no")
    pending = cockpit.pending_plans()
    assert [pv.plan_id for pv in pending] == [p2.id]


def test_pending_plans_filters_by_kind(tmp_path: Path):
    cockpit = _build(tmp_path)
    cockpit.plan_gate.propose(
        kind="k1", payload={"request": "r"}, dod=DoD(), proposed_by="ef"
    )
    cockpit.plan_gate.propose(
        kind="k2", payload={"request": "r"}, dod=DoD(), proposed_by="ef"
    )
    pending_k1 = cockpit.pending_plans(kind="k1")
    assert len(pending_k1) == 1
    assert pending_k1[0].kind == "k1"


def test_pending_plans_include_resolved_overrides_settings(tmp_path: Path):
    cockpit = _build(tmp_path)
    p1 = cockpit.plan_gate.propose(
        kind="k1", payload={"request": "r"}, dod=DoD(), proposed_by="ef"
    )
    cockpit.plan_gate.reject(p1.id, decided_by="user", reason="no")
    assert cockpit.pending_plans() == []
    assert len(cockpit.pending_plans(include_resolved=True)) == 1


def test_pending_plans_respects_max_items_cap(tmp_path: Path):
    cockpit = Cockpit(
        engine=_build(tmp_path).engine,
        plan_gate=_build(tmp_path).plan_gate,
        lifecycle=_build(tmp_path).lifecycle,
        lessons=_build(tmp_path).lessons,
        settings=CockpitSettings(plan_list_max_items=2),
    )
    for i in range(5):
        cockpit.plan_gate.propose(
            kind=f"k{i}",
            payload={"request": "r"},
            dod=DoD(),
            proposed_by="ef",
        )
    assert len(cockpit.pending_plans()) == 2


def test_pending_plans_marks_revision_escalation_with_failed_criteria(
    tmp_path: Path,
):
    cockpit = _build(tmp_path)
    plan = cockpit.plan_gate.propose(
        kind="k1",
        payload={"request": "r", "failed_criteria": ["x", "y"]},
        dod=DoD(),
        proposed_by="orchestrator:revision_escalation",
    )
    [view] = cockpit.pending_plans()
    assert view.is_revision_escalation is True
    assert view.failed_criteria == ["x", "y"]
    assert any("escalated" in h for h in view.diff_hints)


def test_pending_plans_view_has_action_descriptors(tmp_path: Path):
    cockpit = _build(tmp_path)
    cockpit.plan_gate.propose(
        kind="k1", payload={"request": "r"}, dod=DoD(), proposed_by="ef"
    )
    [view] = cockpit.pending_plans()
    ids = [a.id for a in view.actions_available]
    assert ids == ["approve", "reject"]


# ---------- drift


def test_drift_for_unknown_kind_returns_initial_stage(tmp_path: Path):
    cockpit = _build(tmp_path)
    dv = cockpit.drift("never-seen")
    assert dv.current_stage == "proposed"  # initial
    assert dv.outcomes_count == 0
    assert dv.recent_scores == []
    assert dv.drift_warning is False


def test_drift_for_kind_with_outcomes(tmp_path: Path):
    cockpit = _build(tmp_path)
    for _ in range(6):
        cockpit.lifecycle.record_outcome(
            kind="k1", plan_id=None, score=0.6
        )
    dv = cockpit.drift("k1")
    assert dv.outcomes_count > 0
    assert dv.avg_score == pytest.approx(0.6)


def test_drift_overview_sorts_warnings_first(tmp_path: Path):
    cockpit = _build(tmp_path)
    # k1: high scores → no warning
    for _ in range(3):
        cockpit.lifecycle.record_outcome(kind="k1", plan_id=None, score=0.95)
    # k2: near demote threshold → warning
    for _ in range(3):
        cockpit.lifecycle.record_outcome(kind="k2", plan_id=None, score=0.52)
    rows = cockpit.drift_overview()
    assert len(rows) == 2
    assert rows[0].kind == "k2"  # warning first
    assert rows[0].drift_warning is True
    assert rows[1].drift_warning is False


# ---------- summary


def test_summary_one_row_per_kind(tmp_path: Path):
    cockpit = _build(tmp_path)
    for kind in ("k1", "k2", "k3"):
        cockpit.lifecycle.record_outcome(kind=kind, plan_id=None, score=0.8)
    rows = cockpit.summary()
    assert {r.kind for r in rows} == {"k1", "k2", "k3"}
    assert all(r.outcomes_count == 1 for r in rows)


def test_summary_counts_pending_plans_per_kind(tmp_path: Path):
    cockpit = _build(tmp_path)
    cockpit.lifecycle.record_outcome(kind="k1", plan_id=None, score=0.8)
    cockpit.plan_gate.propose(
        kind="k1", payload={"request": "r"}, dod=DoD(), proposed_by="ef"
    )
    cockpit.plan_gate.propose(
        kind="k1", payload={"request": "r"}, dod=DoD(), proposed_by="ef"
    )
    [row] = cockpit.summary()
    assert row.pending_plans == 2


def test_summary_counts_lessons_per_kind(tmp_path: Path):
    cockpit = _build(tmp_path)
    cockpit.lifecycle.record_outcome(kind="k1", plan_id=None, score=0.8)
    cockpit.lessons.record_lesson(
        kind="k1",
        observation="something",
        criteria_hint=[],
    )
    cockpit.lessons.record_lesson(
        kind="k1",
        observation="something else",
        criteria_hint=[],
    )
    [row] = cockpit.summary()
    assert row.lessons_count == 2


# ---------- introspection


def test_known_kinds_lists_observed_kinds(tmp_path: Path):
    cockpit = _build(tmp_path)
    cockpit.lifecycle.record_outcome(kind="alpha", plan_id=None, score=0.8)
    cockpit.lifecycle.record_outcome(kind="beta", plan_id=None, score=0.8)
    assert set(cockpit.known_kinds()) == {"alpha", "beta"}


def test_stage_for_returns_lifecycle_stage(tmp_path: Path):
    cockpit = _build(tmp_path)
    cockpit.lifecycle.set_stage(
        "alpha", LifecycleStage.ROUTINE, reason="test"
    )
    assert cockpit.stage_for("alpha") == LifecycleStage.ROUTINE
