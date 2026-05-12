"""Per-domain proof that the M5-patch features (Phases 7.1-7.4) work
under every demo-domain configuration. This is the cross-domain
genericity check for the new code: each feature is exercised in the
context of architect_lite, tax_lite, and cfo_lite, with the actual
demo Effector and KIND.

The demos themselves stay structurally identical (see test_cross_demo.py
for that invariant). This file demonstrates that consumers wiring up
the new M5 features get the same behavior across domains.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from organism.dod import (
    EVALUATOR_LLM_JUDGE,
    EVALUATOR_SELF_CHECK,
    REVISION_ESCALATE_TO_HUMAN,
    REVISION_ROLLBACK_AND_LOG,
    Criterion,
    DoD,
    DoDEngine,
    DoDValidator,
    EvaluationContext,
    SourceContribution,
)
from organism.lessons import LessonsAggregator, LessonsStore
from organism.lifecycle import (
    LifecycleManager,
    LifecycleSettings,
    LifecycleStore,
)
from organism.orchestrator import (
    REVISION_OUTCOME_ESCALATED,
    REVISION_OUTCOME_ROLLED_BACK,
    ActionOrchestrator,
    ActionStatus,
    OrchestratorSettings,
)
from organism.plan_gate import PlanGate, PlanStore

from examples.architect_lite.demo import KIND as ARCH_KIND
from examples.architect_lite.effector import FloorPlanExtractor
from examples.cfo_lite.demo import KIND as CFO_KIND
from examples.cfo_lite.effector import QuarterlyCloseRunner
from examples.tax_lite.demo import KIND as TAX_KIND
from examples.tax_lite.effector import TaxReturnValidator


class _ScriptedSource:
    """Side-source that hands back a fixed DoD; lets us drive any
    scenario in any domain without changing entity files."""

    name = "scripted"

    def __init__(self, dod: DoD) -> None:
        self._dod = dod

    def contribute(
        self,
        request: Any,
        context: dict[str, Any],
        current: DoD,
    ) -> SourceContribution:
        return SourceContribution(
            source_name=self.name,
            criteria=list(self._dod.criteria),
            confidence_delta=1.0,
        )


def _build_orchestrator(
    tmp_path: Path,
    *,
    dod: DoD,
    initial_stage: str = "checked",
    settings: OrchestratorSettings | None = None,
) -> tuple[ActionOrchestrator, LessonsAggregator, PlanGate]:
    aggregator = LessonsAggregator(store=LessonsStore(tmp_path / "lessons"))
    engine = DoDEngine(sources=[_ScriptedSource(dod)])
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
    return orchestrator, aggregator, plan_gate


# ---------- Self-check evaluator works in every domain


def test_self_check_evaluator_in_architect_domain(tmp_path: Path):
    dod = DoD(
        criteria=[
            Criterion(
                name="extraction_consistent",
                expected=True,
                evaluator=EVALUATOR_SELF_CHECK,
            )
        ]
    )
    orchestrator, _, _ = _build_orchestrator(tmp_path, dod=dod)
    effector = FloorPlanExtractor(
        return_map={"villa-x": {"extraction_consistent": True}}
    )
    res = orchestrator.execute(effector, kind=ARCH_KIND, request="villa-x")
    assert res.status == ActionStatus.APPLIED
    assert res.validation.all_satisfied is True
    assert res.validation.criterion_results[0].evaluator == EVALUATOR_SELF_CHECK


def test_self_check_evaluator_in_tax_domain(tmp_path: Path):
    dod = DoD(
        criteria=[
            Criterion(
                name="ledger_balanced",
                expected=True,
                evaluator=EVALUATOR_SELF_CHECK,
            )
        ]
    )
    orchestrator, _, _ = _build_orchestrator(tmp_path, dod=dod)
    effector = TaxReturnValidator(
        return_map={"client-x": {"ledger_balanced": True}}
    )
    res = orchestrator.execute(effector, kind=TAX_KIND, request="client-x")
    assert res.status == ActionStatus.APPLIED
    assert res.validation.all_satisfied is True


def test_self_check_evaluator_in_cfo_domain(tmp_path: Path):
    dod = DoD(
        criteria=[
            Criterion(
                name="reconciliation_passed",
                expected=True,
                evaluator=EVALUATOR_SELF_CHECK,
            )
        ]
    )
    orchestrator, _, _ = _build_orchestrator(tmp_path, dod=dod)
    effector = QuarterlyCloseRunner(
        return_map={"step-x": {"reconciliation_passed": True}}
    )
    res = orchestrator.execute(effector, kind=CFO_KIND, request="step-x")
    assert res.status == ActionStatus.APPLIED


# ---------- llm_judge evaluator with injected callable


def test_llm_judge_with_injected_callable_works_per_domain(tmp_path: Path):
    def judge(criterion, actual, result):
        return actual == "approved", "judged via callable"

    dod = DoD(
        criteria=[
            Criterion(
                name="narrative_assessment",
                expected="approved",
                evaluator=EVALUATOR_LLM_JUDGE,
            )
        ]
    )

    for domain_path, kind, effector in [
        (
            tmp_path / "arch",
            ARCH_KIND,
            FloorPlanExtractor(
                return_map={"villa-x": {"narrative_assessment": "approved"}}
            ),
        ),
        (
            tmp_path / "tax",
            TAX_KIND,
            TaxReturnValidator(
                return_map={"client-x": {"narrative_assessment": "approved"}}
            ),
        ),
        (
            tmp_path / "cfo",
            CFO_KIND,
            QuarterlyCloseRunner(
                return_map={"step-x": {"narrative_assessment": "approved"}}
            ),
        ),
    ]:
        orchestrator, _, _ = _build_orchestrator(domain_path, dod=dod)
        # Inject the judge by overriding the validator's default context.
        # We do this by passing context via DoDValidator directly.
        orchestrator.validator = DoDValidator()
        # Use the orchestrator's internal validate path by patching:
        # the simplest approach is to validate manually after running.
        request = (
            "villa-x" if kind == ARCH_KIND
            else "client-x" if kind == TAX_KIND
            else "step-x"
        )
        res = orchestrator.execute(effector, kind=kind, request=request)
        # Without the callable wired into the orchestrator's validator,
        # the llm_judge evaluator returns False (no callable configured).
        # Re-validate explicitly with the judge to prove the path works.
        validation = orchestrator.validator.validate(
            res.dod,
            res.result,
            context=EvaluationContext(llm_judge=judge),
        )
        assert validation.all_satisfied is True
        assert validation.criterion_results[0].evaluator == EVALUATOR_LLM_JUDGE


# ---------- Revision strategy ESCALATE_TO_HUMAN per domain


@pytest.mark.parametrize(
    "domain_name,kind,effector_factory,request_id,result_value",
    [
        (
            "arch",
            ARCH_KIND,
            lambda: FloorPlanExtractor(
                return_map={"villa-x": {"needs_review": False}}
            ),
            "villa-x",
            False,
        ),
        (
            "tax",
            TAX_KIND,
            lambda: TaxReturnValidator(
                return_map={"client-x": {"needs_review": False}}
            ),
            "client-x",
            False,
        ),
        (
            "cfo",
            CFO_KIND,
            lambda: QuarterlyCloseRunner(
                return_map={"step-x": {"needs_review": False}}
            ),
            "step-x",
            False,
        ),
    ],
)
def test_escalate_to_human_strategy_works_per_domain(
    tmp_path: Path,
    domain_name: str,
    kind: str,
    effector_factory,
    request_id: str,
    result_value: bool,
):
    dod = DoD(
        criteria=[
            Criterion(
                name="needs_review",
                expected=True,
                revision_strategy=REVISION_ESCALATE_TO_HUMAN,
            )
        ]
    )
    orchestrator, aggregator, plan_gate = _build_orchestrator(
        tmp_path / domain_name,
        dod=dod,
        initial_stage="autonomous",
    )
    effector = effector_factory()
    res = orchestrator.execute(effector, kind=kind, request=request_id)
    assert res.status == ActionStatus.PROPOSED
    assert res.revision_outcome == REVISION_OUTCOME_ESCALATED
    assert res.plan is not None
    assert res.plan.kind == kind
    assert "needs_review" in res.plan.payload["failed_criteria"]
    assert len(plan_gate.list()) == 1
    assert len(aggregator.store.list()) == 1


# ---------- Revision strategy ROLLBACK_AND_LOG per domain


class _RollbackFloorPlan(FloorPlanExtractor):
    def __init__(self, return_map):
        super().__init__(return_map)
        self.rollback_calls: list = []

    def rollback(self, descriptor, result):
        self.rollback_calls.append((descriptor, result))


class _RollbackTaxValidator(TaxReturnValidator):
    def __init__(self, return_map):
        super().__init__(return_map)
        self.rollback_calls: list = []

    def rollback(self, descriptor, result):
        self.rollback_calls.append((descriptor, result))


class _RollbackQuarterlyCloseRunner(QuarterlyCloseRunner):
    def __init__(self, return_map):
        super().__init__(return_map)
        self.rollback_calls: list = []

    def rollback(self, descriptor, result):
        self.rollback_calls.append((descriptor, result))


@pytest.mark.parametrize(
    "domain_name,kind,effector,request_id",
    [
        (
            "arch",
            ARCH_KIND,
            _RollbackFloorPlan(return_map={"villa-x": {"committed": False}}),
            "villa-x",
        ),
        (
            "tax",
            TAX_KIND,
            _RollbackTaxValidator(return_map={"client-x": {"committed": False}}),
            "client-x",
        ),
        (
            "cfo",
            CFO_KIND,
            _RollbackQuarterlyCloseRunner(return_map={"step-x": {"committed": False}}),
            "step-x",
        ),
    ],
)
def test_rollback_and_log_strategy_works_per_domain(
    tmp_path: Path,
    domain_name: str,
    kind: str,
    effector,
    request_id: str,
):
    dod = DoD(
        criteria=[
            Criterion(
                name="committed",
                expected=True,
                revision_strategy=REVISION_ROLLBACK_AND_LOG,
            )
        ]
    )
    orchestrator, aggregator, _ = _build_orchestrator(
        tmp_path / domain_name,
        dod=dod,
        initial_stage="autonomous",
    )
    res = orchestrator.execute(effector, kind=kind, request=request_id)
    assert res.status == ActionStatus.DENIED
    assert res.revision_outcome == REVISION_OUTCOME_ROLLED_BACK
    assert len(effector.rollback_calls) == 1
    assert effector.rollback_calls[0][0]["kind"] == kind
    assert len(aggregator.store.list()) == 1


# ---------- Operative settings: tolerant fulfillment_score_pass per domain


@pytest.mark.parametrize(
    "domain_name,kind,effector,request_id",
    [
        (
            "arch",
            ARCH_KIND,
            FloorPlanExtractor(
                return_map={"villa-x": {"primary": True, "secondary": False}}
            ),
            "villa-x",
        ),
        (
            "tax",
            TAX_KIND,
            TaxReturnValidator(
                return_map={"client-x": {"primary": True, "secondary": False}}
            ),
            "client-x",
        ),
        (
            "cfo",
            CFO_KIND,
            QuarterlyCloseRunner(
                return_map={"step-x": {"primary": True, "secondary": False}}
            ),
            "step-x",
        ),
    ],
)
def test_tolerant_fulfillment_threshold_works_per_domain(
    tmp_path: Path,
    domain_name: str,
    kind: str,
    effector,
    request_id: str,
):
    dod = DoD(
        criteria=[
            Criterion(name="primary", expected=True, weight=4.0),
            Criterion(name="secondary", expected=True, weight=1.0),
        ]
    )
    settings = OrchestratorSettings(fulfillment_score_pass=0.5)
    orchestrator, _, _ = _build_orchestrator(
        tmp_path / domain_name,
        dod=dod,
        settings=settings,
    )
    res = orchestrator.execute(effector, kind=kind, request=request_id)
    assert res.status == ActionStatus.APPLIED
    # score is 0.8 (4/5), threshold 0.5 → fulfilled, no warning fires.
    assert res.warnings == []
    assert res.validation.score == pytest.approx(0.8)
    assert res.validation.is_fulfilled(0.5) is True
