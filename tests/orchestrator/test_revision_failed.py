"""Tests for the REVISION_OUTCOME_FAILED outcome — emitted when the
DoD-Recherche during a revision iteration surfaces a fresh
``clarification_needed``, signalling that the rubric is incoherent
with the request. Distinct from REVISION_OUTCOME_EXHAUSTED (out of
attempts on an otherwise coherent rubric). Mirrors Anthropic Outcomes'
distinction between ``max_iterations_reached`` and ``failed``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

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
    REVISION_OUTCOME_COMPLETED,
    REVISION_OUTCOME_EXHAUSTED,
    REVISION_OUTCOME_FAILED,
    ActionOrchestrator,
    ActionStatus,
    OrchestratorSettings,
)
from organism.plan_gate import PlanGate, PlanStore


class _SwitchingSource:
    """First contribute() returns a clean DoD; second contribute()
    returns a DoD with ``clarification_needed`` — simulates a rubric
    that turns incoherent on re-derivation (e.g. lessons-feedback
    surfaces a contradiction)."""

    name = "switching"

    def __init__(self) -> None:
        self.calls = 0

    def contribute(self, request, context, current):
        self.calls += 1
        if self.calls == 1:
            return SourceContribution(
                source_name=self.name,
                criteria=[Criterion(name="x", expected=True)],
                confidence_delta=1.0,
            )
        return SourceContribution(
            source_name=self.name,
            criteria=[],
            clarifications=["criteria became inconsistent during revision"],
            confidence_delta=0.0,
        )


class _ConstantFailingEffector:
    name = "ef"

    def pre_load(self, ctx):
        return ctx

    def define_done(self, request, context):
        return {}

    def act(self, request):
        return {"x": False}

    def upstream(self, kind, payload):
        pass

    def gate(self, action):
        return True


def _build(tmp_path: Path) -> ActionOrchestrator:
    engine = DoDEngine(sources=[_SwitchingSource()])
    plan_gate = PlanGate(store=PlanStore(tmp_path / "plans"))
    lifecycle = LifecycleManager(
        store=LifecycleStore(tmp_path / "lifecycle"),
        settings=LifecycleSettings(initial_stage="autonomous"),
    )
    aggregator = LessonsAggregator(store=LessonsStore(tmp_path / "lessons"))
    return ActionOrchestrator(
        engine=engine,
        validator=DoDValidator(),
        plan_gate=plan_gate,
        lifecycle=lifecycle,
        lessons_aggregator=aggregator,
        settings=OrchestratorSettings(autonomous_max_revision_attempts=3),
    )


def test_revision_outcome_failed_constant_exported():
    assert REVISION_OUTCOME_FAILED == "failed"


def test_failed_outcome_when_dod_redrive_surfaces_clarification(tmp_path: Path):
    orchestrator = _build(tmp_path)
    effector = _ConstantFailingEffector()
    result = orchestrator.execute(
        effector, kind="k", request="x", context={"kind": "k"}
    )
    assert result.revision_outcome == REVISION_OUTCOME_FAILED
    assert result.status == ActionStatus.NEEDS_CLARIFICATION
    assert "incoherent" in result.reason


def test_failed_does_not_set_revision_pending(tmp_path: Path):
    orchestrator = _build(tmp_path)
    effector = _ConstantFailingEffector()
    result = orchestrator.execute(
        effector, kind="k", request="x", context={"kind": "k"}
    )
    assert result.revision_pending is False


def test_failed_distinct_from_exhausted():
    # Sanity: the two values are not the same string. The distinction
    # between "rubric is the wrong shape" (failed) and "ran out of
    # tries on a correct rubric" (exhausted) is the whole point.
    assert REVISION_OUTCOME_FAILED != REVISION_OUTCOME_EXHAUSTED
    assert REVISION_OUTCOME_FAILED != REVISION_OUTCOME_COMPLETED
