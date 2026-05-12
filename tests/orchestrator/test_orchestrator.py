from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from organism.dod import (
    Criterion,
    DoD,
    DoDEngine,
    DoDValidator,
    SourceContribution,
)
from organism.lifecycle import (
    LifecycleManager,
    LifecycleSettings,
    LifecycleStage,
    LifecycleStore,
)
from organism.orchestrator import (
    ActionOrchestrator,
    ActionResult,
    ActionStatus,
)
from organism.plan_gate import PlanGate, PlanStatus, PlanStore


# ----- Test fixtures (synthetic, no domain bias) -----


class _StaticDoDSource:
    def __init__(
        self,
        criteria: list[Criterion] | None = None,
        confidence_delta: float = 1.0,
        clarifications: list[str] | None = None,
    ) -> None:
        self.name = "test_source"
        self._criteria = criteria or []
        self._confidence_delta = confidence_delta
        self._clarifications = clarifications or []

    def contribute(
        self,
        request: Any,
        context: dict[str, Any],
        current: DoD,
    ) -> SourceContribution:
        return SourceContribution(
            source_name=self.name,
            criteria=[
                Criterion(name=c.name, expected=c.expected, weight=c.weight)
                for c in self._criteria
            ],
            confidence_delta=self._confidence_delta,
            clarifications=list(self._clarifications),
        )


class _TestEffector:
    name = "test_effector"

    def __init__(
        self,
        act_returns: dict[str, Any] | None = None,
        gate_returns: bool = True,
    ) -> None:
        self.act_returns = act_returns or {"approved": True}
        self.gate_returns = gate_returns
        self.act_calls: list[Any] = []
        self.pre_load_calls: list[dict[str, Any]] = []
        self.upstream_calls: list[tuple[str, dict[str, Any]]] = []
        self.gate_calls: list[dict[str, Any]] = []

    def pre_load(self, context: dict[str, Any]) -> dict[str, Any]:
        self.pre_load_calls.append(context)
        return {**context, "preloaded": True}

    def define_done(
        self, request: Any, context: dict[str, Any]
    ) -> dict[str, Any]:
        return {}

    def act(self, request: Any) -> Any:
        self.act_calls.append(request)
        return self.act_returns

    def upstream(self, kind: str, payload: dict[str, Any]) -> None:
        self.upstream_calls.append((kind, payload))

    def gate(self, action: dict[str, Any]) -> bool:
        self.gate_calls.append(action)
        return self.gate_returns


def _build_orchestrator(
    tmp_path: Path,
    *,
    criteria: list[Criterion] | None = None,
    clarifications: list[str] | None = None,
    initial_stage: str = "proposed",
    promote_after_n: int = 30,
    demote_after_n: int = 5,
) -> tuple[ActionOrchestrator, LifecycleManager, PlanGate]:
    source = _StaticDoDSource(
        criteria=criteria
        or [Criterion(name="approved", expected=True, weight=1.0)],
        clarifications=clarifications,
    )
    engine = DoDEngine(sources=[source])
    validator = DoDValidator()
    plan_store = PlanStore(tmp_path / "plans")
    plan_gate = PlanGate(store=plan_store)
    lifecycle_store = LifecycleStore(tmp_path / "lifecycle")
    lifecycle = LifecycleManager(
        store=lifecycle_store,
        settings=LifecycleSettings(
            initial_stage=initial_stage,
            promote_after_n=promote_after_n,
            demote_after_n=demote_after_n,
            window_size=max(promote_after_n, demote_after_n) + 5,
        ),
    )
    orchestrator = ActionOrchestrator(
        engine=engine,
        validator=validator,
        plan_gate=plan_gate,
        lifecycle=lifecycle,
    )
    return orchestrator, lifecycle, plan_gate


# ----- Stage MANUAL -----


def test_manual_stage_returns_manual_status_without_running(tmp_path: Path):
    orchestrator, lifecycle, _ = _build_orchestrator(
        tmp_path, initial_stage="manual"
    )
    effector = _TestEffector()
    result = orchestrator.execute(
        effector, kind="k", request="any"
    )
    assert result.status == ActionStatus.MANUAL
    assert effector.act_calls == []
    assert "manual" in result.reason


# ----- Stage PROPOSED -----


def test_proposed_stage_creates_plan_and_does_not_run(tmp_path: Path):
    orchestrator, _, plan_gate = _build_orchestrator(tmp_path)
    effector = _TestEffector()
    result = orchestrator.execute(
        effector, kind="k", request="hello", context={"a": 1}
    )
    assert result.status == ActionStatus.PROPOSED
    assert result.plan is not None
    assert result.plan.kind == "k"
    assert result.plan.status == PlanStatus.PROPOSED
    assert result.plan.proposed_by == "test_effector"
    assert effector.act_calls == []
    # Plan is persisted
    assert plan_gate.get(result.plan.id).id == result.plan.id


def test_proposed_stage_uses_explicit_proposed_by(tmp_path: Path):
    orchestrator, _, _ = _build_orchestrator(tmp_path)
    effector = _TestEffector()
    result = orchestrator.execute(
        effector,
        kind="k",
        request="hello",
        proposed_by="custom_actor",
    )
    assert result.plan.proposed_by == "custom_actor"


def test_proposed_stage_payload_contains_request_and_context(tmp_path: Path):
    orchestrator, _, _ = _build_orchestrator(tmp_path)
    effector = _TestEffector()
    result = orchestrator.execute(
        effector, kind="k", request={"x": 1}, context={"y": 2}
    )
    assert result.plan.payload["request"] == {"x": 1}
    # context was enriched by pre_load
    assert result.plan.payload["context"]["y"] == 2
    assert result.plan.payload["context"]["preloaded"] is True


# ----- Stage CHECKED -----


def test_checked_stage_runs_action_and_validates(tmp_path: Path):
    orchestrator, _, _ = _build_orchestrator(
        tmp_path, initial_stage="checked"
    )
    effector = _TestEffector(act_returns={"approved": True})
    result = orchestrator.execute(
        effector, kind="k", request="hello"
    )
    assert result.status == ActionStatus.APPLIED
    assert result.result == {"approved": True}
    assert result.validation is not None
    assert result.validation.all_satisfied is True
    assert result.validation.score == 1.0
    assert effector.act_calls == ["hello"]


def test_checked_stage_records_outcome_in_lifecycle(tmp_path: Path):
    orchestrator, lifecycle, _ = _build_orchestrator(
        tmp_path, initial_stage="checked"
    )
    effector = _TestEffector(act_returns={"approved": True})
    orchestrator.execute(effector, kind="k", request="x")
    state = lifecycle.get_state("k")
    assert len(state.recent_outcomes) == 1
    assert state.recent_outcomes[0].score == 1.0


def test_checked_stage_with_failed_validation_records_low_score(
    tmp_path: Path,
):
    orchestrator, lifecycle, _ = _build_orchestrator(
        tmp_path, initial_stage="checked"
    )
    effector = _TestEffector(act_returns={"approved": False})
    result = orchestrator.execute(
        effector, kind="k", request="x"
    )
    assert result.status == ActionStatus.APPLIED
    assert result.validation.all_satisfied is False
    assert result.validation.score == 0.0
    state = lifecycle.get_state("k")
    assert state.recent_outcomes[0].score == 0.0


# ----- Stage AUTONOMOUS -----


def test_autonomous_stage_with_passing_validation_no_revision(tmp_path: Path):
    orchestrator, _, _ = _build_orchestrator(
        tmp_path, initial_stage="autonomous"
    )
    effector = _TestEffector(act_returns={"approved": True})
    result = orchestrator.execute(effector, kind="k", request="x")
    assert result.status == ActionStatus.APPLIED
    assert result.revision_pending is False


def test_autonomous_stage_with_failing_validation_flags_revision(
    tmp_path: Path,
):
    orchestrator, _, _ = _build_orchestrator(
        tmp_path, initial_stage="autonomous"
    )
    effector = _TestEffector(act_returns={"approved": False})
    result = orchestrator.execute(effector, kind="k", request="x")
    assert result.status == ActionStatus.APPLIED
    assert result.revision_pending is True


def test_checked_stage_does_not_flag_revision_on_failure(tmp_path: Path):
    orchestrator, _, _ = _build_orchestrator(
        tmp_path, initial_stage="checked"
    )
    effector = _TestEffector(act_returns={"approved": False})
    result = orchestrator.execute(effector, kind="k", request="x")
    assert result.revision_pending is False


# ----- Effector.gate denial -----


def test_gate_denial_returns_denied_status(tmp_path: Path):
    orchestrator, _, _ = _build_orchestrator(
        tmp_path, initial_stage="checked"
    )
    effector = _TestEffector(gate_returns=False)
    result = orchestrator.execute(effector, kind="k", request="x")
    assert result.status == ActionStatus.DENIED
    assert effector.act_calls == []
    assert "gate" in result.reason


def test_gate_receives_kind_and_request(tmp_path: Path):
    orchestrator, _, _ = _build_orchestrator(
        tmp_path, initial_stage="checked"
    )
    effector = _TestEffector()
    orchestrator.execute(effector, kind="my_kind", request={"data": 1})
    assert effector.gate_calls[0] == {"kind": "my_kind", "request": {"data": 1}}


# ----- DoD with clarification -----


def test_clarification_blocks_execution(tmp_path: Path):
    orchestrator, _, _ = _build_orchestrator(
        tmp_path,
        initial_stage="checked",
        clarifications=["What is X?"],
    )
    effector = _TestEffector()
    result = orchestrator.execute(effector, kind="k", request="x")
    assert result.status == ActionStatus.NEEDS_CLARIFICATION
    assert "What is X?" in result.dod.clarification_needed
    assert effector.act_calls == []


# ----- pre_load is called -----


def test_execute_calls_pre_load_with_caller_context(tmp_path: Path):
    orchestrator, _, _ = _build_orchestrator(
        tmp_path, initial_stage="checked"
    )
    effector = _TestEffector()
    orchestrator.execute(
        effector, kind="k", request="x", context={"a": 1}
    )
    assert len(effector.pre_load_calls) == 1
    assert effector.pre_load_calls[0] == {"a": 1}


def test_execute_does_not_pollute_caller_context(tmp_path: Path):
    orchestrator, _, _ = _build_orchestrator(
        tmp_path, initial_stage="checked"
    )
    effector = _TestEffector()
    caller_ctx = {"a": 1}
    orchestrator.execute(
        effector, kind="k", request="x", context=caller_ctx
    )
    assert caller_ctx == {"a": 1}


# ----- apply_approved_plan -----


def test_apply_approved_plan_full_flow(tmp_path: Path):
    orchestrator, lifecycle, plan_gate = _build_orchestrator(tmp_path)
    effector = _TestEffector(act_returns={"approved": True})
    propose_result = orchestrator.execute(
        effector, kind="k", request="x"
    )
    assert propose_result.status == ActionStatus.PROPOSED

    plan_id = propose_result.plan.id
    plan_gate.approve(plan_id, decided_by="user_a", reason="ok")

    apply_result = orchestrator.apply_approved_plan(plan_id, effector)
    assert apply_result.status == ActionStatus.APPLIED
    assert apply_result.result == {"approved": True}
    assert apply_result.validation.all_satisfied is True
    assert apply_result.plan.status == PlanStatus.APPLIED
    assert effector.act_calls == ["x"]

    # Lifecycle outcome recorded with plan_id
    state = lifecycle.get_state("k")
    assert state.recent_outcomes[0].plan_id == plan_id


def test_apply_proposed_plan_raises(tmp_path: Path):
    orchestrator, _, _ = _build_orchestrator(tmp_path)
    effector = _TestEffector()
    propose_result = orchestrator.execute(
        effector, kind="k", request="x"
    )
    with pytest.raises(ValueError, match="status is 'proposed'"):
        orchestrator.apply_approved_plan(
            propose_result.plan.id, effector
        )


def test_apply_rejected_plan_raises(tmp_path: Path):
    orchestrator, _, plan_gate = _build_orchestrator(tmp_path)
    effector = _TestEffector()
    propose_result = orchestrator.execute(
        effector, kind="k", request="x"
    )
    plan_gate.reject(propose_result.plan.id, decided_by="user_a")
    with pytest.raises(ValueError, match="status is 'rejected'"):
        orchestrator.apply_approved_plan(
            propose_result.plan.id, effector
        )


def test_apply_with_gate_denial_returns_denied(tmp_path: Path):
    orchestrator, _, plan_gate = _build_orchestrator(tmp_path)
    effector = _TestEffector(gate_returns=False)
    propose_result = orchestrator.execute(
        effector, kind="k", request="x"
    )
    plan_gate.approve(propose_result.plan.id, decided_by="user_a")
    apply_result = orchestrator.apply_approved_plan(
        propose_result.plan.id, effector
    )
    assert apply_result.status == ActionStatus.DENIED


# ----- Stage-Transition durch Orchestrator-Outcomes -----


def test_repeated_high_score_outcomes_promote_stage(tmp_path: Path):
    orchestrator, lifecycle, _ = _build_orchestrator(
        tmp_path,
        initial_stage="checked",
        promote_after_n=3,
    )
    effector = _TestEffector(act_returns={"approved": True})
    for _ in range(3):
        orchestrator.execute(effector, kind="k", request="x")
    state = lifecycle.get_state("k")
    assert state.stage == LifecycleStage.ROUTINE
