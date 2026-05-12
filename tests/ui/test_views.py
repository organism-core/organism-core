from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from organism.dod import (
    EVALUATOR_LLM_JUDGE,
    EVALUATOR_RULE,
    EVALUATOR_SELF_CHECK,
    REVISION_ESCALATE_TO_HUMAN,
    REVISION_ROLLBACK_AND_LOG,
    Criterion,
    DoD,
)
from organism.lifecycle.settings import LifecycleSettings
from organism.lifecycle.types import (
    ActionOutcome,
    LifecycleStage,
    LifecycleState,
    LifecycleTransition,
)
from organism.plan_gate.types import Plan, PlanStatus
from organism.ui.views import (
    ApprovalAction,
    CriterionView,
    DoDView,
    DriftView,
    PlanApprovalView,
    _trend_bucket,
)


# ---------- CriterionView


def test_criterion_view_from_criterion_marks_rule_as_non_qualitative():
    c = Criterion(name="x", expected=42, weight=2.0, source="entity")
    cv = CriterionView.from_criterion(c)
    assert cv.name == "x"
    assert cv.expected_display == "42"
    assert cv.weight == 2.0
    assert cv.evaluator == EVALUATOR_RULE
    assert cv.source == "entity"
    assert cv.is_qualitative is False
    assert cv.revision_strategy is None


def test_criterion_view_marks_llm_judge_as_qualitative():
    c = Criterion(name="tone", expected="formal", evaluator=EVALUATOR_LLM_JUDGE)
    cv = CriterionView.from_criterion(c)
    assert cv.is_qualitative is True


def test_criterion_view_truncates_long_expected():
    c = Criterion(name="x", expected="a" * 200)
    cv = CriterionView.from_criterion(c)
    assert len(cv.expected_display) == 60


# ---------- DoDView


def test_dod_view_sorts_criteria_by_weight_desc():
    dod = DoD(
        criteria=[
            Criterion(name="a", expected=1, weight=0.5),
            Criterion(name="b", expected=1, weight=2.0),
            Criterion(name="c", expected=1, weight=1.0),
        ]
    )
    dv = DoDView.from_dod(dod)
    assert [c.name for c in dv.criteria] == ["b", "c", "a"]


def test_dod_view_total_weight_and_confidence():
    dod = DoD(
        criteria=[
            Criterion(name="a", expected=1, weight=1.0),
            Criterion(name="b", expected=1, weight=0.5),
        ],
        confidence=0.85,
    )
    dv = DoDView.from_dod(dod)
    assert dv.total_weight == 1.5
    assert dv.confidence == 0.85


def test_dod_view_evaluator_breakdown():
    dod = DoD(
        criteria=[
            Criterion(name="a", expected=1),
            Criterion(name="b", expected=True, evaluator=EVALUATOR_SELF_CHECK),
            Criterion(name="c", expected=True, evaluator=EVALUATOR_SELF_CHECK),
            Criterion(name="d", expected="ok", evaluator=EVALUATOR_LLM_JUDGE),
        ]
    )
    dv = DoDView.from_dod(dod)
    assert dv.evaluator_breakdown == {
        EVALUATOR_RULE: 1,
        EVALUATOR_SELF_CHECK: 2,
        EVALUATOR_LLM_JUDGE: 1,
    }
    assert dv.qualitative_count == 3


def test_dod_view_revision_strategy_summary():
    dod = DoD(
        criteria=[
            Criterion(
                name="a",
                expected=1,
                revision_strategy=REVISION_ESCALATE_TO_HUMAN,
            ),
            Criterion(
                name="b",
                expected=1,
                revision_strategy=REVISION_ROLLBACK_AND_LOG,
            ),
            Criterion(
                name="c",
                expected=1,
                revision_strategy=REVISION_ESCALATE_TO_HUMAN,
            ),
            Criterion(name="d", expected=1),  # None — not counted
        ]
    )
    dv = DoDView.from_dod(dod)
    assert dv.revision_strategy_summary == {
        REVISION_ESCALATE_TO_HUMAN: 2,
        REVISION_ROLLBACK_AND_LOG: 1,
    }


def test_dod_view_provenance_summary_counts_per_source():
    dod = DoD(
        criteria=[
            Criterion(name="a", expected=1, source="entity"),
            Criterion(name="b", expected=1, source="entity"),
            Criterion(name="c", expected=1, source="lessons"),
        ],
        _provenance={"entity": ["a", "b"], "lessons": ["c"]},
    )
    dv = DoDView.from_dod(dod)
    assert dv.provenance_summary == {"entity": 2, "lessons": 1}


def test_dod_view_to_dict_round_trip_data():
    dod = DoD(
        criteria=[Criterion(name="x", expected=1)],
        confidence=0.5,
        evidence_sources=["self_check"],
    )
    d = DoDView.from_dod(dod).to_dict()
    assert d["confidence"] == 0.5
    assert d["criteria"][0]["name"] == "x"
    assert d["evidence_sources"] == ["self_check"]


# ---------- PlanApprovalView


def _make_plan(
    *,
    status: PlanStatus = PlanStatus.PROPOSED,
    proposed_by: str = "ef",
    payload: dict | None = None,
    proposed_at: datetime | None = None,
) -> Plan:
    return Plan(
        id="plan-x",
        kind="my_kind",
        payload=payload or {"request": "req-1", "context": {"a": 1}},
        dod=DoD(criteria=[Criterion(name="x", expected=True)]),
        status=status,
        proposed_by=proposed_by,
        proposed_at=proposed_at or datetime(2026, 5, 10, tzinfo=timezone.utc),
    )


def test_plan_approval_view_proposed_offers_approve_and_reject():
    plan = _make_plan(status=PlanStatus.PROPOSED)
    pv = PlanApprovalView.from_plan(plan, payload_repr_max_length=120)
    ids = [a.id for a in pv.actions_available]
    assert ids == ["approve", "reject"]
    assert pv.actions_available[0].severity == "primary"
    assert pv.actions_available[1].severity == "danger"
    assert pv.actions_available[1].requires_reason is True


def test_plan_approval_view_resolved_offers_no_actions():
    for status in (
        PlanStatus.APPROVED,
        PlanStatus.REJECTED,
        PlanStatus.APPLIED,
        PlanStatus.EXPIRED,
    ):
        plan = _make_plan(status=status)
        pv = PlanApprovalView.from_plan(plan, payload_repr_max_length=120)
        assert pv.actions_available == []


def test_plan_approval_view_revision_escalation_flag():
    plan = _make_plan(
        proposed_by="orchestrator:revision_escalation",
        payload={
            "request": "req",
            "context": {},
            "failed_criteria": ["a", "b"],
        },
    )
    pv = PlanApprovalView.from_plan(plan, payload_repr_max_length=120)
    assert pv.is_revision_escalation is True
    assert pv.failed_criteria == ["a", "b"]


def test_plan_approval_view_request_summary_truncated():
    plan = _make_plan(payload={"request": "x" * 500})
    pv = PlanApprovalView.from_plan(plan, payload_repr_max_length=80)
    assert len(pv.request_summary) <= 80


def test_plan_approval_view_payload_excludes_request_key():
    plan = _make_plan(payload={"request": "r", "context": {"k": 1}, "extra": "v"})
    pv = PlanApprovalView.from_plan(plan, payload_repr_max_length=80)
    assert "request" not in pv.payload_summary
    assert "context" in pv.payload_summary
    assert "extra" in pv.payload_summary


def test_plan_approval_view_age_seconds_computed_when_proposed():
    proposed = datetime(2026, 5, 10, 12, 0, 0, tzinfo=timezone.utc)
    plan = _make_plan(proposed_at=proposed)
    later = proposed + timedelta(minutes=5)
    pv = PlanApprovalView.from_plan(
        plan,
        payload_repr_max_length=120,
        now_iso=later.isoformat(),
    )
    assert pv.age_seconds == 300.0


def test_plan_approval_view_age_seconds_none_when_resolved():
    plan = _make_plan(status=PlanStatus.APPROVED)
    pv = PlanApprovalView.from_plan(plan, payload_repr_max_length=120)
    assert pv.age_seconds is None


def test_plan_approval_view_diff_hints_passed_through():
    plan = _make_plan()
    pv = PlanApprovalView.from_plan(
        plan,
        payload_repr_max_length=120,
        diff_hints=["3 prior decided plans of this kind"],
    )
    assert pv.diff_hints == ["3 prior decided plans of this kind"]


# ---------- DriftView


def _make_state(
    *,
    stage: LifecycleStage,
    scores: list[float],
) -> LifecycleState:
    now = datetime.now(timezone.utc)
    return LifecycleState(
        kind="my_kind",
        stage=stage,
        recent_outcomes=[
            ActionOutcome(plan_id=None, score=s, recorded_at=now)
            for s in scores
        ],
    )


def _default_settings() -> LifecycleSettings:
    return LifecycleSettings(
        initial_stage="proposed",
        promote_after_n=3,
        promote_score_threshold=0.9,
        demote_after_n=2,
        demote_score_threshold=0.5,
        window_size=10,
    )


def test_drift_view_avg_and_distances():
    state = _make_state(
        stage=LifecycleStage.CHECKED,
        scores=[0.6, 0.6, 0.6, 0.6, 0.6, 0.6],
    )
    settings = _default_settings()
    dv = DriftView.from_state(
        state, settings, trend_window=6, drift_warning_band=0.05
    )
    assert dv.avg_score == pytest.approx(0.6)
    assert dv.distance_to_promote == pytest.approx(-0.3)
    assert dv.distance_to_demote == pytest.approx(0.1)


def test_drift_view_trend_improving():
    state = _make_state(
        stage=LifecycleStage.CHECKED,
        scores=[0.3, 0.3, 0.3, 0.9, 0.9, 0.9],
    )
    settings = _default_settings()
    dv = DriftView.from_state(
        state, settings, trend_window=6, drift_warning_band=0.05
    )
    assert dv.score_trend == "improving"


def test_drift_view_trend_degrading():
    state = _make_state(
        stage=LifecycleStage.CHECKED,
        scores=[0.9, 0.9, 0.9, 0.3, 0.3, 0.3],
    )
    settings = _default_settings()
    dv = DriftView.from_state(
        state, settings, trend_window=6, drift_warning_band=0.05
    )
    assert dv.score_trend == "degrading"


def test_drift_view_trend_stable():
    state = _make_state(
        stage=LifecycleStage.CHECKED,
        scores=[0.7, 0.7, 0.7, 0.7, 0.7, 0.7],
    )
    settings = _default_settings()
    dv = DriftView.from_state(
        state, settings, trend_window=6, drift_warning_band=0.05
    )
    assert dv.score_trend == "stable"


def test_drift_view_warning_when_avg_close_to_demote():
    # avg = 0.52, demote threshold = 0.5, band = 0.05 → within band → warning
    state = _make_state(
        stage=LifecycleStage.CHECKED,
        scores=[0.5, 0.55, 0.5, 0.55, 0.5, 0.55],
    )
    settings = _default_settings()
    dv = DriftView.from_state(
        state, settings, trend_window=6, drift_warning_band=0.05
    )
    assert dv.drift_warning is True


def test_drift_view_warning_when_avg_below_demote():
    state = _make_state(
        stage=LifecycleStage.CHECKED,
        scores=[0.1, 0.2, 0.1, 0.2, 0.1, 0.2],
    )
    settings = _default_settings()
    dv = DriftView.from_state(
        state, settings, trend_window=6, drift_warning_band=0.05
    )
    assert dv.drift_warning is True


def test_drift_view_no_warning_when_avg_well_above_demote():
    state = _make_state(
        stage=LifecycleStage.CHECKED,
        scores=[0.9, 0.9, 0.9, 0.9, 0.9, 0.9],
    )
    settings = _default_settings()
    dv = DriftView.from_state(
        state, settings, trend_window=6, drift_warning_band=0.05
    )
    assert dv.drift_warning is False


def test_drift_view_stage_neighbors():
    state = _make_state(stage=LifecycleStage.CHECKED, scores=[0.5])
    settings = _default_settings()
    dv = DriftView.from_state(
        state, settings, trend_window=6, drift_warning_band=0.05
    )
    assert dv.stage_above == "routine"
    assert dv.stage_below == "proposed"


def test_drift_view_stage_neighbors_at_top():
    state = _make_state(stage=LifecycleStage.AUTONOMOUS, scores=[0.95])
    settings = _default_settings()
    dv = DriftView.from_state(
        state, settings, trend_window=6, drift_warning_band=0.05
    )
    assert dv.stage_above is None
    assert dv.stage_below == "routine"


def test_drift_view_includes_last_transition_when_present():
    state = _make_state(stage=LifecycleStage.CHECKED, scores=[0.7, 0.7])
    state.transition_history.append(
        LifecycleTransition(
            from_stage=LifecycleStage.PROPOSED,
            to_stage=LifecycleStage.CHECKED,
            reason="manual override",
            transitioned_at=datetime.now(timezone.utc),
        )
    )
    settings = _default_settings()
    dv = DriftView.from_state(
        state, settings, trend_window=6, drift_warning_band=0.05
    )
    assert dv.last_transition is not None
    assert dv.last_transition["to_stage"] == "checked"
    assert dv.transition_count == 1


# ---------- Trend bucket helper


def test_trend_bucket_unknown_for_short_series():
    assert _trend_bucket([]) == "unknown"
    assert _trend_bucket([0.5]) == "unknown"


def test_trend_bucket_picks_improving_above_threshold():
    assert _trend_bucket([0.3, 0.3, 0.5, 0.5]) == "improving"


def test_trend_bucket_picks_degrading_below_threshold():
    assert _trend_bucket([0.9, 0.9, 0.3, 0.3]) == "degrading"


# ---------- ApprovalAction


def test_approval_action_to_dict_includes_all_fields():
    a = ApprovalAction(
        id="approve",
        label="Approve",
        severity="primary",
        requires_confirmation=True,
        requires_reason=False,
        confirmation_prompt="ok?",
    )
    d = a.to_dict()
    assert d == {
        "id": "approve",
        "label": "Approve",
        "severity": "primary",
        "requires_confirmation": True,
        "requires_reason": False,
        "confirmation_prompt": "ok?",
        "available": True,
    }
