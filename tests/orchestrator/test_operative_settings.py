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
from organism.lessons import LessonsAggregator, LessonsStore
from organism.lifecycle import (
    LifecycleManager,
    LifecycleSettings,
    LifecycleStore,
)
from organism.orchestrator import (
    ActionOrchestrator,
    ActionStatus,
    OrchestratorSettings,
)
from organism.plan_gate import PlanGate, PlanStore


# ---------- Settings validation


def test_invalid_on_definition_unclear_rejected():
    with pytest.raises(ValueError, match="on_definition_unclear"):
        OrchestratorSettings(on_definition_unclear="explode")


def test_invalid_on_fulfillment_failed_rejected():
    with pytest.raises(ValueError, match="on_fulfillment_failed"):
        OrchestratorSettings(on_fulfillment_failed="explode")


def test_invalid_fulfillment_score_pass_rejected():
    with pytest.raises(ValueError, match="fulfillment_score_pass"):
        OrchestratorSettings(fulfillment_score_pass=1.5)


def test_default_settings_are_strict():
    s = OrchestratorSettings()
    assert s.on_definition_unclear == "ask"
    assert s.on_fulfillment_failed == "warn"
    assert s.fulfillment_score_pass == 1.0


# ---------- ValidationResult.is_fulfilled


def test_is_fulfilled_strict_default():
    from organism.dod.validator import CriterionResult, ValidationResult

    vr = ValidationResult(
        criterion_results=[
            CriterionResult(
                name="a",
                satisfied=False,
                weight=1.0,
                expected=1,
                actual=2,
            )
        ],
        score=0.0,
    )
    assert vr.is_fulfilled(1.0) is False
    assert vr.is_fulfilled(0.0) is True


def test_is_fulfilled_tolerant_threshold():
    from organism.dod.validator import CriterionResult, ValidationResult

    vr = ValidationResult(
        criterion_results=[
            CriterionResult(
                name="a", satisfied=True, weight=4.0, expected=1, actual=1
            ),
            CriterionResult(
                name="b", satisfied=False, weight=1.0, expected=1, actual=2
            ),
        ],
        score=0.8,
    )
    assert vr.is_fulfilled(0.8) is True
    assert vr.is_fulfilled(0.9) is False


def test_is_fulfilled_empty_criteria_passes_any_threshold():
    from organism.dod.validator import ValidationResult

    vr = ValidationResult()
    assert vr.is_fulfilled(0.0) is True
    assert vr.is_fulfilled(1.0) is True


# ---------- Test fixtures


class _BaseSource:
    def __init__(
        self,
        name: str,
        criteria: list[Criterion],
        clarifications: list[str] | None = None,
        confidence_delta: float = 1.0,
    ) -> None:
        self.name = name
        self._criteria = criteria
        self._clarifications = list(clarifications or [])
        self._confidence_delta = confidence_delta

    def contribute(
        self,
        request: Any,
        context: dict[str, Any],
        current: DoD,
    ) -> SourceContribution:
        return SourceContribution(
            source_name=self.name,
            criteria=[
                Criterion(
                    name=c.name,
                    expected=c.expected,
                    weight=c.weight,
                    evaluator=c.evaluator,
                )
                for c in self._criteria
            ],
            clarifications=list(self._clarifications),
            confidence_delta=self._confidence_delta,
        )


class _Effector:
    name = "ef"

    def __init__(self, results: list[Any]) -> None:
        self._results = list(results)
        self.act_count = 0
        self.rollback_calls: list[tuple[dict, Any]] = []

    def pre_load(self, ctx):
        return ctx

    def define_done(self, request, context):
        return {}

    def act(self, request):
        idx = min(self.act_count, len(self._results) - 1)
        self.act_count += 1
        return self._results[idx]

    def upstream(self, kind, payload):
        pass

    def gate(self, action):
        return True

    def rollback(self, action_descriptor, action_result):
        self.rollback_calls.append((action_descriptor, action_result))


def _build(
    tmp_path: Path,
    *,
    base_criteria: list[Criterion],
    clarifications: list[str] | None = None,
    initial_stage: str = "checked",
    settings: OrchestratorSettings | None = None,
) -> tuple[ActionOrchestrator, LessonsAggregator]:
    base_source = _BaseSource(
        name="base",
        criteria=base_criteria,
        clarifications=clarifications,
        confidence_delta=1.0,
    )
    aggregator = LessonsAggregator(store=LessonsStore(tmp_path / "lessons"))
    engine = DoDEngine(sources=[base_source])
    plan_gate = PlanGate(store=PlanStore(tmp_path / "plans"))
    lifecycle = LifecycleManager(
        store=LifecycleStore(tmp_path / "lifecycle"),
        settings=LifecycleSettings(initial_stage=initial_stage),
    )
    orchestrator = ActionOrchestrator(
        engine=engine,
        validator=DoDValidator(),
        plan_gate=plan_gate,
        lifecycle=lifecycle,
        lessons_aggregator=aggregator,
        settings=settings or OrchestratorSettings(),
    )
    return orchestrator, aggregator


# ---------- on_definition_unclear


def test_on_definition_unclear_ask_returns_needs_clarification(tmp_path: Path):
    orchestrator, _ = _build(
        tmp_path,
        base_criteria=[Criterion(name="x", expected=True)],
        clarifications=["what is x?"],
    )
    effector = _Effector(results=[{"x": True}])
    result = orchestrator.execute(effector, kind="k", request="x")
    assert result.status == ActionStatus.NEEDS_CLARIFICATION
    assert effector.act_count == 0


def test_on_definition_unclear_abort_returns_denied(tmp_path: Path):
    orchestrator, _ = _build(
        tmp_path,
        base_criteria=[Criterion(name="x", expected=True)],
        clarifications=["what is x?", "what is y?"],
        settings=OrchestratorSettings(on_definition_unclear="abort"),
    )
    effector = _Effector(results=[{"x": True}])
    result = orchestrator.execute(effector, kind="k", request="x")
    assert result.status == ActionStatus.DENIED
    assert "on_definition_unclear=abort" in result.reason
    assert "what is x?" in result.reason
    assert effector.act_count == 0


def test_on_definition_unclear_proceed_runs_with_warning(tmp_path: Path):
    orchestrator, _ = _build(
        tmp_path,
        base_criteria=[Criterion(name="x", expected=True)],
        clarifications=["should we proceed?"],
        settings=OrchestratorSettings(
            on_definition_unclear="proceed_with_warning"
        ),
    )
    effector = _Effector(results=[{"x": True}])
    result = orchestrator.execute(effector, kind="k", request="x")
    assert result.status == ActionStatus.APPLIED
    assert effector.act_count == 1
    assert any(
        "proceed_with_warning" in w for w in result.warnings
    )
    assert any("should we proceed?" in w for w in result.warnings)


# ---------- on_fulfillment_failed (non-AUTONOMOUS)


def test_on_fulfillment_failed_warn_default(tmp_path: Path):
    orchestrator, _ = _build(
        tmp_path,
        base_criteria=[Criterion(name="x", expected=True)],
        initial_stage="checked",
    )
    effector = _Effector(results=[{"x": False}])
    result = orchestrator.execute(effector, kind="k", request="x")
    assert result.status == ActionStatus.APPLIED
    assert any("on_fulfillment_failed=warn" in w for w in result.warnings)
    assert effector.act_count == 1


def test_on_fulfillment_failed_retry_succeeds_on_second(tmp_path: Path):
    orchestrator, _ = _build(
        tmp_path,
        base_criteria=[Criterion(name="x", expected=True)],
        initial_stage="checked",
        settings=OrchestratorSettings(on_fulfillment_failed="retry"),
    )
    effector = _Effector(results=[{"x": False}, {"x": True}])
    result = orchestrator.execute(effector, kind="k", request="x")
    assert result.status == ActionStatus.APPLIED
    assert effector.act_count == 2
    assert result.warnings == []


def test_on_fulfillment_failed_retry_exhausts_with_warning(tmp_path: Path):
    orchestrator, _ = _build(
        tmp_path,
        base_criteria=[Criterion(name="x", expected=True)],
        initial_stage="checked",
        settings=OrchestratorSettings(on_fulfillment_failed="retry"),
    )
    effector = _Effector(results=[{"x": False}])
    result = orchestrator.execute(effector, kind="k", request="x")
    assert result.status == ActionStatus.APPLIED
    assert effector.act_count == 2  # initial + single retry
    assert any("retry exhausted" in w for w in result.warnings)


def test_on_fulfillment_failed_abort_calls_rollback(tmp_path: Path):
    orchestrator, _ = _build(
        tmp_path,
        base_criteria=[Criterion(name="x", expected=True)],
        initial_stage="checked",
        settings=OrchestratorSettings(on_fulfillment_failed="abort"),
    )
    effector = _Effector(results=[{"x": False}])
    result = orchestrator.execute(effector, kind="k", request="x")
    assert result.status == ActionStatus.DENIED
    assert len(effector.rollback_calls) == 1
    assert "on_fulfillment_failed=abort" in result.reason


def test_on_fulfillment_failed_does_not_apply_to_autonomous(tmp_path: Path):
    """In AUTONOMOUS, revision strategies handle failures, not the
    operative on_fulfillment_failed setting."""
    orchestrator, _ = _build(
        tmp_path,
        base_criteria=[Criterion(name="x", expected=True)],
        initial_stage="autonomous",
        settings=OrchestratorSettings(
            autonomous_max_revision_attempts=0,
            on_fulfillment_failed="abort",  # would fire on non-AUTONOMOUS
        ),
    )
    effector = _Effector(results=[{"x": False}])
    result = orchestrator.execute(effector, kind="k", request="x")
    # AUTONOMOUS: revision_pending=True, no abort/rollback.
    assert result.status == ActionStatus.APPLIED
    assert result.revision_pending is True
    assert len(effector.rollback_calls) == 0


# ---------- fulfillment_score_pass tolerance


def test_tolerant_threshold_skips_warn(tmp_path: Path):
    """With fulfillment_score_pass=0.5 and weighted score 0.8, the action
    is considered fulfilled even if one criterion fails — no warning."""
    orchestrator, _ = _build(
        tmp_path,
        base_criteria=[
            Criterion(name="a", expected=True, weight=4.0),
            Criterion(name="b", expected=True, weight=1.0),
        ],
        initial_stage="checked",
        settings=OrchestratorSettings(fulfillment_score_pass=0.5),
    )
    effector = _Effector(results=[{"a": True, "b": False}])
    result = orchestrator.execute(effector, kind="k", request="x")
    assert result.status == ActionStatus.APPLIED
    assert result.warnings == []
    # validation reports the failure, but it's below the action-level
    # fulfillment threshold of 0.5 → no policy fires.
    assert result.validation.score == pytest.approx(0.8)
    assert result.validation.all_satisfied is False


def test_tolerant_threshold_still_warns_below_pass(tmp_path: Path):
    orchestrator, _ = _build(
        tmp_path,
        base_criteria=[
            Criterion(name="a", expected=True, weight=1.0),
            Criterion(name="b", expected=True, weight=1.0),
        ],
        initial_stage="checked",
        settings=OrchestratorSettings(fulfillment_score_pass=0.6),
    )
    effector = _Effector(results=[{"a": False, "b": False}])
    result = orchestrator.execute(effector, kind="k", request="x")
    assert result.status == ActionStatus.APPLIED
    # score 0.0 < 0.6 → policy fires → warn
    assert any("on_fulfillment_failed=warn" in w for w in result.warnings)


def test_tolerant_threshold_in_autonomous_skips_revision(tmp_path: Path):
    orchestrator, aggregator = _build(
        tmp_path,
        base_criteria=[
            Criterion(name="a", expected=True, weight=4.0),
            Criterion(name="b", expected=True, weight=1.0),
        ],
        initial_stage="autonomous",
        settings=OrchestratorSettings(
            autonomous_max_revision_attempts=2,
            fulfillment_score_pass=0.5,
        ),
    )
    effector = _Effector(results=[{"a": True, "b": False}])
    result = orchestrator.execute(effector, kind="k", request="x")
    # Score 0.8 >= 0.5 → fulfilled → no revision.
    assert result.revision_attempts == 0
    assert result.revision_pending is False
    assert aggregator.store.list() == []
