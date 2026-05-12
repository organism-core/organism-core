from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from organism.dod import (
    REVISION_ESCALATE_TO_HUMAN,
    REVISION_RETRY_ALT_PARAMS,
    REVISION_ROLLBACK_AND_LOG,
    Criterion,
    DoD,
    DoDEngine,
    DoDValidator,
    SourceContribution,
)
from organism.dod.sources.lessons import LessonsSource
from organism.lessons import LessonsAggregator, LessonsStore
from organism.lifecycle import (
    LifecycleManager,
    LifecycleSettings,
    LifecycleStore,
)
from organism.orchestrator import (
    REVISION_OUTCOME_COMPLETED,
    REVISION_OUTCOME_ESCALATED,
    REVISION_OUTCOME_EXHAUSTED,
    REVISION_OUTCOME_ROLLED_BACK,
    ActionOrchestrator,
    ActionStatus,
    OrchestratorSettings,
)
from organism.plan_gate import PlanGate, PlanStore


# Strategy validation on Criterion


def test_criterion_rejects_unknown_revision_strategy():
    with pytest.raises(ValueError, match="unknown revision_strategy"):
        Criterion(name="x", expected=1, revision_strategy="vibes")


def test_criterion_accepts_none_strategy_default():
    c = Criterion(name="x", expected=1)
    assert c.revision_strategy is None


def test_criterion_revision_strategy_round_trip():
    c = Criterion(
        name="x",
        expected=True,
        revision_strategy=REVISION_ROLLBACK_AND_LOG,
    )
    assert Criterion.from_dict(c.to_dict()) == c


def test_criterion_to_dict_omits_default_strategy():
    d = Criterion(name="x", expected=1).to_dict()
    assert "revision_strategy" not in d


# Settings validation


def test_settings_rejects_unknown_default_strategy():
    with pytest.raises(ValueError, match="default_revision_strategy"):
        OrchestratorSettings(default_revision_strategy="bogus")


# Test fixtures (mirrors test_autonomous_revision.py style)


class _BaseSource:
    def __init__(
        self,
        name: str,
        criteria: list[Criterion],
        confidence_delta: float = 1.0,
    ) -> None:
        self.name = name
        self._criteria = criteria
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
                    revision_strategy=c.revision_strategy,
                )
                for c in self._criteria
            ],
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


class _NoRollbackEffector(_Effector):
    """Effector that does NOT implement rollback — verifies hasattr-fallback."""

    def __init__(self, results: list[Any]) -> None:
        super().__init__(results)
        del self.__class__.rollback  # type: ignore[attr-defined]

    def pre_load(self, ctx):
        return ctx


def _build(
    tmp_path: Path,
    *,
    base_criteria: list[Criterion],
    effector: _Effector,
    max_attempts: int = 2,
    default_strategy: str = REVISION_RETRY_ALT_PARAMS,
) -> tuple[ActionOrchestrator, LessonsAggregator, PlanGate]:
    base_source = _BaseSource(
        name="base",
        criteria=base_criteria,
        confidence_delta=1.0,
    )
    aggregator = LessonsAggregator(store=LessonsStore(tmp_path / "lessons"))
    lessons_source = LessonsSource(aggregator=aggregator)

    engine = DoDEngine(sources=[base_source, lessons_source])
    plan_gate = PlanGate(store=PlanStore(tmp_path / "plans"))
    lifecycle = LifecycleManager(
        store=LifecycleStore(tmp_path / "lifecycle"),
        settings=LifecycleSettings(initial_stage="autonomous"),
    )
    orchestrator = ActionOrchestrator(
        engine=engine,
        validator=DoDValidator(),
        plan_gate=plan_gate,
        lifecycle=lifecycle,
        lessons_aggregator=aggregator,
        settings=OrchestratorSettings(
            autonomous_max_revision_attempts=max_attempts,
            default_revision_strategy=default_strategy,
        ),
    )
    return orchestrator, aggregator, plan_gate


# ESCALATE_TO_HUMAN


def test_escalate_to_human_creates_plan_and_returns_proposed(tmp_path: Path):
    orchestrator, aggregator, plan_gate = _build(
        tmp_path,
        base_criteria=[
            Criterion(
                name="needs_review",
                expected=True,
                revision_strategy=REVISION_ESCALATE_TO_HUMAN,
            )
        ],
        effector=_Effector(results=[{"needs_review": False}]),
    )
    result = orchestrator.execute(
        next(iter([_Effector(results=[{"needs_review": False}])])),
        kind="k",
        request="x",
    )
    assert result.status == ActionStatus.PROPOSED
    assert result.revision_outcome == REVISION_OUTCOME_ESCALATED
    assert result.plan is not None
    assert "needs_review" in result.plan.payload["failed_criteria"]
    # Plan is recorded by the gate.
    plans = plan_gate.list()
    assert len(plans) == 1
    assert plans[0].proposed_by == "orchestrator:revision_escalation"
    # A lesson was still written.
    assert len(aggregator.store.list()) == 1


def test_escalate_to_human_does_not_retry(tmp_path: Path):
    effector = _Effector(results=[{"x": False}, {"x": True}])
    orchestrator, _, _ = _build(
        tmp_path,
        base_criteria=[
            Criterion(
                name="x",
                expected=True,
                revision_strategy=REVISION_ESCALATE_TO_HUMAN,
            )
        ],
        effector=effector,
    )
    orchestrator.execute(effector, kind="k", request="x")
    # Only the initial act, no retry.
    assert effector.act_count == 1


# ROLLBACK_AND_LOG


def test_rollback_and_log_calls_effector_rollback(tmp_path: Path):
    effector = _Effector(results=[{"x": False}])
    orchestrator, aggregator, _ = _build(
        tmp_path,
        base_criteria=[
            Criterion(
                name="x",
                expected=True,
                revision_strategy=REVISION_ROLLBACK_AND_LOG,
            )
        ],
        effector=effector,
    )
    result = orchestrator.execute(effector, kind="k", request="x")
    assert result.status == ActionStatus.DENIED
    assert result.revision_outcome == REVISION_OUTCOME_ROLLED_BACK
    assert len(effector.rollback_calls) == 1
    descriptor, action_result = effector.rollback_calls[0]
    assert descriptor == {"kind": "k", "request": "x"}
    assert action_result == {"x": False}
    assert len(aggregator.store.list()) == 1


def test_rollback_skipped_silently_when_effector_has_no_method(tmp_path: Path):
    class _NoRollback:
        name = "ef"

        def pre_load(self, ctx):
            return ctx

        def define_done(self, r, c):
            return {}

        def act(self, request):
            return {"x": False}

        def upstream(self, k, p):
            pass

        def gate(self, action):
            return True

    effector = _NoRollback()
    orchestrator, aggregator, _ = _build(
        tmp_path,
        base_criteria=[
            Criterion(
                name="x",
                expected=True,
                revision_strategy=REVISION_ROLLBACK_AND_LOG,
            )
        ],
        effector=_Effector(results=[{"x": False}]),  # placeholder
    )
    result = orchestrator.execute(effector, kind="k", request="x")
    # Even without a rollback method, the action ends with rolled_back state.
    assert result.status == ActionStatus.DENIED
    assert result.revision_outcome == REVISION_OUTCOME_ROLLED_BACK
    assert len(aggregator.store.list()) == 1


def test_rollback_failure_is_captured_as_lesson(tmp_path: Path):
    class _BadRollback(_Effector):
        def rollback(self, descriptor, result):  # type: ignore[override]
            raise RuntimeError("disk full")

    effector = _BadRollback(results=[{"x": False}])
    orchestrator, aggregator, _ = _build(
        tmp_path,
        base_criteria=[
            Criterion(
                name="x",
                expected=True,
                revision_strategy=REVISION_ROLLBACK_AND_LOG,
            )
        ],
        effector=effector,
    )
    result = orchestrator.execute(effector, kind="k", request="x")
    assert result.status == ActionStatus.DENIED
    lessons = aggregator.store.list()
    # Two lessons: dod_failure + rollback_failure.
    sources = [l.provenance.source for l in lessons]
    assert "dod_failure" in sources
    assert "rollback_failure" in sources


# RETRY_ALT_PARAMS still default-behavior


def test_retry_alt_params_remains_default_strategy(tmp_path: Path):
    effector = _Effector(results=[{"x": False}, {"x": True}])
    orchestrator, _, _ = _build(
        tmp_path,
        base_criteria=[Criterion(name="x", expected=True)],
        effector=effector,
    )
    result = orchestrator.execute(effector, kind="k", request="x")
    assert result.revision_outcome == REVISION_OUTCOME_COMPLETED
    assert result.revision_attempts == 1
    assert result.status == ActionStatus.APPLIED


def test_retry_exhausted_yields_outcome_exhausted(tmp_path: Path):
    effector = _Effector(results=[{"x": False}])
    orchestrator, _, _ = _build(
        tmp_path,
        base_criteria=[Criterion(name="x", expected=True)],
        effector=effector,
        max_attempts=2,
    )
    result = orchestrator.execute(effector, kind="k", request="x")
    assert result.revision_outcome == REVISION_OUTCOME_EXHAUSTED
    assert result.revision_pending is True
    assert result.revision_attempts == 2


# Priority — strongest strategy wins


def test_priority_rollback_beats_escalate_beats_retry(tmp_path: Path):
    effector = _Effector(results=[{"a": False, "b": False, "c": False}])
    orchestrator, _, _ = _build(
        tmp_path,
        base_criteria=[
            Criterion(
                name="a",
                expected=True,
                revision_strategy=REVISION_RETRY_ALT_PARAMS,
            ),
            Criterion(
                name="b",
                expected=True,
                revision_strategy=REVISION_ESCALATE_TO_HUMAN,
            ),
            Criterion(
                name="c",
                expected=True,
                revision_strategy=REVISION_ROLLBACK_AND_LOG,
            ),
        ],
        effector=effector,
    )
    result = orchestrator.execute(effector, kind="k", request="x")
    # rollback wins over escalate and retry.
    assert result.revision_outcome == REVISION_OUTCOME_ROLLED_BACK


def test_priority_escalate_beats_retry(tmp_path: Path):
    effector = _Effector(results=[{"a": False, "b": False}])
    orchestrator, _, _ = _build(
        tmp_path,
        base_criteria=[
            Criterion(
                name="a",
                expected=True,
                revision_strategy=REVISION_RETRY_ALT_PARAMS,
            ),
            Criterion(
                name="b",
                expected=True,
                revision_strategy=REVISION_ESCALATE_TO_HUMAN,
            ),
        ],
        effector=effector,
    )
    result = orchestrator.execute(effector, kind="k", request="x")
    assert result.revision_outcome == REVISION_OUTCOME_ESCALATED


def test_default_strategy_used_when_criterion_strategy_is_none(tmp_path: Path):
    effector = _Effector(results=[{"x": False}])
    orchestrator, _, _ = _build(
        tmp_path,
        base_criteria=[
            Criterion(
                name="x", expected=True, revision_strategy=None
            )
        ],
        effector=effector,
        default_strategy=REVISION_ROLLBACK_AND_LOG,
    )
    result = orchestrator.execute(effector, kind="k", request="x")
    assert result.revision_outcome == REVISION_OUTCOME_ROLLED_BACK
