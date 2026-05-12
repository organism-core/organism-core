from __future__ import annotations

from datetime import datetime, timezone

from organism.lifecycle.settings import LifecycleSettings
from organism.lifecycle.store import LifecycleStore
from organism.lifecycle.types import (
    ActionOutcome,
    LifecycleStage,
    LifecycleState,
    LifecycleTransition,
    stage_above,
    stage_below,
)


class LifecycleManager:
    def __init__(
        self,
        store: LifecycleStore,
        settings: LifecycleSettings | None = None,
    ) -> None:
        self.store = store
        self.settings = settings or LifecycleSettings()

    def get_stage(self, kind: str) -> LifecycleStage:
        return self.get_state(kind).stage

    def get_state(self, kind: str) -> LifecycleState:
        if self.store.exists(kind):
            return self.store.read(kind)
        return LifecycleState(
            kind=kind,
            stage=LifecycleStage(self.settings.initial_stage),
        )

    def set_stage(
        self,
        kind: str,
        stage: LifecycleStage,
        reason: str = "manual override",
    ) -> LifecycleState:
        state = self.get_state(kind)
        if state.stage == stage:
            self.store.write(state)
            return state
        transition = LifecycleTransition(
            from_stage=state.stage,
            to_stage=stage,
            reason=reason,
            transitioned_at=_now(),
        )
        state.stage = stage
        state.last_transition_at = transition.transitioned_at
        state.transition_history.append(transition)
        state.recent_outcomes = []
        self.store.write(state)
        return state

    def record_outcome(
        self,
        kind: str,
        plan_id: str | None,
        score: float,
    ) -> tuple[LifecycleState, LifecycleTransition | None]:
        state = self.get_state(kind)
        outcome = ActionOutcome(
            plan_id=plan_id,
            score=score,
            recorded_at=_now(),
        )
        state.recent_outcomes.append(outcome)

        if len(state.recent_outcomes) > self.settings.window_size:
            state.recent_outcomes = state.recent_outcomes[
                -self.settings.window_size :
            ]

        transition = self.evaluate_transition(state)
        if transition is not None:
            state.stage = transition.to_stage
            state.last_transition_at = transition.transitioned_at
            state.transition_history.append(transition)
            state.recent_outcomes = []

        self.store.write(state)
        return state, transition

    def evaluate_transition(
        self, state: LifecycleState
    ) -> LifecycleTransition | None:
        outcomes = state.recent_outcomes
        if not outcomes:
            return None

        # Demote check first — drift takes priority over promotion.
        demote_window = outcomes[-self.settings.demote_after_n :]
        if len(demote_window) >= self.settings.demote_after_n:
            avg = _avg_score(demote_window)
            if avg < self.settings.demote_score_threshold:
                target = stage_below(state.stage)
                if target is not None:
                    return LifecycleTransition(
                        from_stage=state.stage,
                        to_stage=target,
                        reason=(
                            f"demote: avg of last "
                            f"{self.settings.demote_after_n} = {avg:.3f} "
                            f"< {self.settings.demote_score_threshold}"
                        ),
                        transitioned_at=_now(),
                    )

        # Promote check.
        promote_window = outcomes[-self.settings.promote_after_n :]
        if len(promote_window) >= self.settings.promote_after_n:
            avg = _avg_score(promote_window)
            if avg >= self.settings.promote_score_threshold:
                target = stage_above(state.stage)
                if target is not None:
                    return LifecycleTransition(
                        from_stage=state.stage,
                        to_stage=target,
                        reason=(
                            f"promote: avg of last "
                            f"{self.settings.promote_after_n} = {avg:.3f} "
                            f">= {self.settings.promote_score_threshold}"
                        ),
                        transitioned_at=_now(),
                    )

        return None


def _avg_score(outcomes: list[ActionOutcome]) -> float:
    return sum(o.score for o in outcomes) / len(outcomes)


def _now() -> datetime:
    return datetime.now(timezone.utc)
