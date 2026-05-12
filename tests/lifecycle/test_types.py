from __future__ import annotations

from datetime import datetime, timezone

from organism.lifecycle import (
    STAGE_ORDER,
    ActionOutcome,
    LifecycleStage,
    LifecycleState,
    LifecycleTransition,
    stage_above,
    stage_below,
)


def test_stage_values():
    assert LifecycleStage.MANUAL.value == "manual"
    assert LifecycleStage.PROPOSED.value == "proposed"
    assert LifecycleStage.CHECKED.value == "checked"
    assert LifecycleStage.ROUTINE.value == "routine"
    assert LifecycleStage.AUTONOMOUS.value == "autonomous"


def test_stage_order_is_linear():
    assert STAGE_ORDER == (
        LifecycleStage.MANUAL,
        LifecycleStage.PROPOSED,
        LifecycleStage.CHECKED,
        LifecycleStage.ROUTINE,
        LifecycleStage.AUTONOMOUS,
    )


def test_stage_above_returns_next_stage():
    assert stage_above(LifecycleStage.MANUAL) == LifecycleStage.PROPOSED
    assert stage_above(LifecycleStage.PROPOSED) == LifecycleStage.CHECKED
    assert stage_above(LifecycleStage.CHECKED) == LifecycleStage.ROUTINE
    assert stage_above(LifecycleStage.ROUTINE) == LifecycleStage.AUTONOMOUS


def test_stage_above_at_top_returns_none():
    assert stage_above(LifecycleStage.AUTONOMOUS) is None


def test_stage_below_returns_prev_stage():
    assert stage_below(LifecycleStage.AUTONOMOUS) == LifecycleStage.ROUTINE
    assert stage_below(LifecycleStage.ROUTINE) == LifecycleStage.CHECKED
    assert stage_below(LifecycleStage.CHECKED) == LifecycleStage.PROPOSED
    assert stage_below(LifecycleStage.PROPOSED) == LifecycleStage.MANUAL


def test_stage_below_at_bottom_returns_none():
    assert stage_below(LifecycleStage.MANUAL) is None


def test_action_outcome_round_trip():
    o = ActionOutcome(
        plan_id="plan-1",
        score=0.85,
        recorded_at=datetime(2026, 5, 9, 10, 0, 0, tzinfo=timezone.utc),
    )
    restored = ActionOutcome.from_dict(o.to_dict())
    assert restored == o


def test_action_outcome_with_no_plan_id():
    o = ActionOutcome(
        plan_id=None,
        score=0.5,
        recorded_at=datetime(2026, 5, 9, 10, 0, 0, tzinfo=timezone.utc),
    )
    restored = ActionOutcome.from_dict(o.to_dict())
    assert restored.plan_id is None


def test_lifecycle_transition_round_trip():
    t = LifecycleTransition(
        from_stage=LifecycleStage.PROPOSED,
        to_stage=LifecycleStage.CHECKED,
        reason="promote: avg = 0.95",
        transitioned_at=datetime(
            2026, 5, 9, 11, 0, 0, tzinfo=timezone.utc
        ),
    )
    restored = LifecycleTransition.from_dict(t.to_dict())
    assert restored == t


def test_lifecycle_state_minimal_round_trip():
    s = LifecycleState(
        kind="my_kind",
        stage=LifecycleStage.PROPOSED,
    )
    restored = LifecycleState.from_dict(s.to_dict())
    assert restored == s


def test_lifecycle_state_full_round_trip():
    outcomes = [
        ActionOutcome(
            plan_id=f"p-{i}",
            score=0.9,
            recorded_at=datetime(
                2026, 5, 9, 10, i, 0, tzinfo=timezone.utc
            ),
        )
        for i in range(3)
    ]
    transitions = [
        LifecycleTransition(
            from_stage=LifecycleStage.PROPOSED,
            to_stage=LifecycleStage.CHECKED,
            reason="promoted via test",
            transitioned_at=datetime(
                2026, 5, 9, 11, 0, 0, tzinfo=timezone.utc
            ),
        ),
    ]
    s = LifecycleState(
        kind="my_kind",
        stage=LifecycleStage.CHECKED,
        recent_outcomes=outcomes,
        last_transition_at=datetime(
            2026, 5, 9, 11, 0, 0, tzinfo=timezone.utc
        ),
        transition_history=transitions,
    )
    restored = LifecycleState.from_dict(s.to_dict())
    assert restored == s
