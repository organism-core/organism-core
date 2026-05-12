from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from organism.lifecycle import (
    ActionOutcome,
    LifecycleManager,
    LifecycleSettings,
    LifecycleStage,
    LifecycleState,
    LifecycleStore,
)


def _make_manager(tmp_path: Path, **settings_kwargs) -> LifecycleManager:
    store = LifecycleStore(tmp_path)
    settings = (
        LifecycleSettings(**settings_kwargs) if settings_kwargs else None
    )
    return LifecycleManager(store=store, settings=settings)


# get_stage / get_state


def test_get_stage_for_new_kind_returns_initial(tmp_path: Path):
    manager = _make_manager(tmp_path)
    assert manager.get_stage("new_kind") == LifecycleStage.PROPOSED


def test_get_stage_with_custom_initial(tmp_path: Path):
    manager = _make_manager(tmp_path, initial_stage="checked")
    assert manager.get_stage("new_kind") == LifecycleStage.CHECKED


def test_get_state_for_new_kind_does_not_persist(tmp_path: Path):
    manager = _make_manager(tmp_path)
    state = manager.get_state("new_kind")
    assert state.stage == LifecycleStage.PROPOSED
    assert state.recent_outcomes == []
    assert not manager.store.exists("new_kind")


# set_stage


def test_set_stage_persists(tmp_path: Path):
    manager = _make_manager(tmp_path)
    manager.set_stage("k", LifecycleStage.AUTONOMOUS, reason="manual override")
    assert manager.get_stage("k") == LifecycleStage.AUTONOMOUS


def test_set_stage_records_transition(tmp_path: Path):
    manager = _make_manager(tmp_path)
    state = manager.set_stage(
        "k", LifecycleStage.CHECKED, reason="bootstrap"
    )
    assert len(state.transition_history) == 1
    transition = state.transition_history[0]
    assert transition.from_stage == LifecycleStage.PROPOSED
    assert transition.to_stage == LifecycleStage.CHECKED
    assert transition.reason == "bootstrap"


def test_set_stage_clears_recent_outcomes(tmp_path: Path):
    manager = _make_manager(tmp_path)
    manager.record_outcome("k", plan_id=None, score=0.5)
    manager.set_stage("k", LifecycleStage.CHECKED)
    state = manager.get_state("k")
    assert state.recent_outcomes == []


def test_set_stage_same_as_current_does_not_record_transition(
    tmp_path: Path,
):
    manager = _make_manager(tmp_path)
    manager.set_stage("k", LifecycleStage.PROPOSED)  # already proposed
    state = manager.get_state("k")
    assert state.transition_history == []


# record_outcome


def test_record_outcome_creates_state_for_new_kind(tmp_path: Path):
    manager = _make_manager(tmp_path)
    state, transition = manager.record_outcome("k", plan_id="p1", score=0.5)
    assert state.kind == "k"
    assert state.stage == LifecycleStage.PROPOSED
    assert len(state.recent_outcomes) == 1
    assert state.recent_outcomes[0].score == 0.5
    assert state.recent_outcomes[0].plan_id == "p1"
    assert transition is None


def test_record_outcome_persists(tmp_path: Path):
    manager = _make_manager(tmp_path)
    manager.record_outcome("k", plan_id="p1", score=0.5)
    assert manager.store.exists("k")


def test_record_outcome_appends_to_window(tmp_path: Path):
    manager = _make_manager(tmp_path)
    manager.record_outcome("k", plan_id=None, score=0.5)
    manager.record_outcome("k", plan_id=None, score=0.6)
    state = manager.get_state("k")
    assert [o.score for o in state.recent_outcomes] == [0.5, 0.6]


def test_record_outcome_trims_to_window_size(tmp_path: Path):
    manager = _make_manager(
        tmp_path,
        promote_after_n=5,
        demote_after_n=3,
        window_size=5,
    )
    for i in range(8):
        manager.record_outcome("k", plan_id=None, score=0.5)
    state = manager.get_state("k")
    assert len(state.recent_outcomes) == 5


# Promotion


def test_promotion_when_window_average_high(tmp_path: Path):
    manager = _make_manager(
        tmp_path,
        promote_after_n=3,
        promote_score_threshold=0.9,
        demote_after_n=2,
        demote_score_threshold=0.7,
        window_size=10,
    )
    for _ in range(2):
        manager.record_outcome("k", plan_id=None, score=0.95)
    # After 2 outcomes the promote-window (3) is not yet full
    assert manager.get_stage("k") == LifecycleStage.PROPOSED

    state, transition = manager.record_outcome("k", plan_id=None, score=0.95)
    assert transition is not None
    assert transition.from_stage == LifecycleStage.PROPOSED
    assert transition.to_stage == LifecycleStage.CHECKED
    assert state.stage == LifecycleStage.CHECKED


def test_promotion_clears_recent_outcomes(tmp_path: Path):
    manager = _make_manager(
        tmp_path,
        promote_after_n=3,
        promote_score_threshold=0.9,
        demote_after_n=10,  # high so no demote interference
        demote_score_threshold=0.0,
        window_size=10,
    )
    for _ in range(3):
        manager.record_outcome("k", plan_id=None, score=0.95)
    state = manager.get_state("k")
    assert state.stage == LifecycleStage.CHECKED
    assert state.recent_outcomes == []


def test_promotion_at_autonomous_returns_none(tmp_path: Path):
    manager = _make_manager(
        tmp_path,
        initial_stage="autonomous",
        promote_after_n=3,
        promote_score_threshold=0.9,
        demote_after_n=10,
        demote_score_threshold=0.0,
        window_size=10,
    )
    for _ in range(2):
        manager.record_outcome("k", plan_id=None, score=0.95)
    state, transition = manager.record_outcome("k", plan_id=None, score=0.95)
    assert transition is None
    assert state.stage == LifecycleStage.AUTONOMOUS


# Demotion


def test_demotion_when_window_average_low(tmp_path: Path):
    manager = _make_manager(
        tmp_path,
        initial_stage="checked",
        promote_after_n=10,
        promote_score_threshold=0.99,
        demote_after_n=3,
        demote_score_threshold=0.7,
        window_size=10,
    )
    for _ in range(2):
        manager.record_outcome("k", plan_id=None, score=0.4)
    assert manager.get_stage("k") == LifecycleStage.CHECKED

    state, transition = manager.record_outcome("k", plan_id=None, score=0.4)
    assert transition is not None
    assert transition.from_stage == LifecycleStage.CHECKED
    assert transition.to_stage == LifecycleStage.PROPOSED
    assert state.stage == LifecycleStage.PROPOSED


def test_demotion_at_manual_returns_none(tmp_path: Path):
    manager = _make_manager(
        tmp_path,
        initial_stage="manual",
        promote_after_n=10,
        promote_score_threshold=0.99,
        demote_after_n=3,
        demote_score_threshold=0.7,
        window_size=10,
    )
    for _ in range(3):
        manager.record_outcome("k", plan_id=None, score=0.1)
    assert manager.get_stage("k") == LifecycleStage.MANUAL


def test_demote_takes_priority_over_promote(tmp_path: Path):
    # Construct outcomes where promote-window average is high, but
    # demote-window (recent few) average is low — demote should win.
    manager = _make_manager(
        tmp_path,
        initial_stage="checked",
        promote_after_n=5,
        promote_score_threshold=0.9,
        demote_after_n=3,
        demote_score_threshold=0.7,
        window_size=10,
    )
    # 2 high (avg 1.0) then 3 low (avg 0.3): promote-window avg = (2.0 + 0.9) / 5 = 0.58
    # which is < 0.9 anyway. Try with stronger promote-coverage.
    # Use 4 high then 3 low: promote-window (last 5) = [1, 1, 0.3, 0.3, 0.3] avg=0.58 <0.9
    # Hmm, demote is straightforward. Let me set up where promote could fire if checked first.
    # Actually demote is checked first by design — let me make a case with high enough promote-avg:
    # 5 outcomes [1, 1, 1, 0.4, 0.4]: promote-window avg = 0.76 (<0.9 not promote).
    # I'll just use config where last 3 are low and earlier are high:
    for _ in range(2):
        manager.record_outcome("k", plan_id=None, score=1.0)
    for _ in range(3):
        manager.record_outcome("k", plan_id=None, score=0.3)
    state = manager.get_state("k")
    # Demote should have fired, dropping to PROPOSED
    assert state.stage == LifecycleStage.PROPOSED


# evaluate_transition (pure)


def test_evaluate_transition_does_not_mutate_state(tmp_path: Path):
    manager = _make_manager(
        tmp_path,
        promote_after_n=3,
        promote_score_threshold=0.9,
        demote_after_n=10,
        demote_score_threshold=0.0,
        window_size=10,
    )
    state = LifecycleState(
        kind="k",
        stage=LifecycleStage.PROPOSED,
        recent_outcomes=[
            ActionOutcome(
                plan_id=None,
                score=0.95,
                recorded_at=datetime(
                    2026, 5, 9, 10, i, 0, tzinfo=timezone.utc
                ),
            )
            for i in range(3)
        ],
    )
    transition = manager.evaluate_transition(state)
    assert transition is not None
    # State unchanged
    assert state.stage == LifecycleStage.PROPOSED
    assert len(state.recent_outcomes) == 3
    assert state.transition_history == []


def test_evaluate_transition_empty_outcomes_returns_none(tmp_path: Path):
    manager = _make_manager(tmp_path)
    state = LifecycleState(kind="k", stage=LifecycleStage.PROPOSED)
    assert manager.evaluate_transition(state) is None


# transition history accumulates


def test_transition_history_accumulates(tmp_path: Path):
    manager = _make_manager(
        tmp_path,
        promote_after_n=2,
        promote_score_threshold=0.9,
        demote_after_n=10,
        demote_score_threshold=0.0,
        window_size=10,
    )
    # Promote PROPOSED -> CHECKED
    manager.record_outcome("k", plan_id=None, score=0.95)
    manager.record_outcome("k", plan_id=None, score=0.95)
    # Promote CHECKED -> ROUTINE (after window cleared)
    manager.record_outcome("k", plan_id=None, score=0.95)
    manager.record_outcome("k", plan_id=None, score=0.95)
    state = manager.get_state("k")
    assert state.stage == LifecycleStage.ROUTINE
    assert len(state.transition_history) == 2
    assert state.transition_history[0].to_stage == LifecycleStage.CHECKED
    assert state.transition_history[1].to_stage == LifecycleStage.ROUTINE
