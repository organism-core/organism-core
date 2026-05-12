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
from organism.lifecycle import (
    LifecycleManager,
    LifecycleSettings,
    LifecycleStore,
)
from organism.observability import TraceStore, TraceStoreSettings
from organism.orchestrator import ActionOrchestrator, ActionStatus
from organism.plan_gate import PlanGate, PlanStore


class _StaticSource:
    def __init__(
        self,
        criteria: list[Criterion] | None = None,
        clarifications: list[str] | None = None,
    ) -> None:
        self.name = "test_source"
        self._criteria = criteria or []
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
            confidence_delta=1.0,
            clarifications=list(self._clarifications),
        )


class _TestEffector:
    name = "test_effector"

    def __init__(
        self,
        act_returns: Any = None,
        gate_returns: bool = True,
    ) -> None:
        self.act_returns = (
            act_returns if act_returns is not None else {"approved": True}
        )
        self.gate_returns = gate_returns

    def pre_load(self, context: dict[str, Any]) -> dict[str, Any]:
        return {**context, "preloaded": True}

    def define_done(
        self, request: Any, context: dict[str, Any]
    ) -> dict[str, Any]:
        return {}

    def act(self, request: Any) -> Any:
        return self.act_returns

    def upstream(self, kind: str, payload: dict[str, Any]) -> None:
        pass

    def gate(self, action: dict[str, Any]) -> bool:
        return self.gate_returns


def _build_orchestrator(
    tmp_path: Path,
    *,
    initial_stage: str = "checked",
    criteria: list[Criterion] | None = None,
    clarifications: list[str] | None = None,
    trace_enabled: bool = True,
    trace_store: TraceStore | None | object = "default",
) -> tuple[ActionOrchestrator, TraceStore | None]:
    source = _StaticSource(
        criteria=criteria
        or [Criterion(name="approved", expected=True, weight=1.0)],
        clarifications=clarifications,
    )
    engine = DoDEngine(sources=[source])
    validator = DoDValidator()
    plan_gate = PlanGate(store=PlanStore(tmp_path / "plans"))
    lifecycle = LifecycleManager(
        store=LifecycleStore(tmp_path / "lifecycle"),
        settings=LifecycleSettings(initial_stage=initial_stage),
    )

    if trace_store == "default":
        store = TraceStore(tmp_path / "traces")
    else:
        store = trace_store

    orchestrator = ActionOrchestrator(
        engine=engine,
        validator=validator,
        plan_gate=plan_gate,
        lifecycle=lifecycle,
        trace_store=store,
        trace_settings=TraceStoreSettings(enabled=trace_enabled),
    )
    return orchestrator, store


# ----- Recording -----


def test_execute_records_trace_when_store_provided(tmp_path: Path):
    orchestrator, trace_store = _build_orchestrator(tmp_path)
    effector = _TestEffector()
    orchestrator.execute(effector, kind="k", request="hello")
    traces = trace_store.list()
    assert len(traces) == 1
    assert traces[0].kind == "k"
    assert traces[0].status == ActionStatus.APPLIED


def test_execute_does_not_record_when_no_store(tmp_path: Path):
    orchestrator, _ = _build_orchestrator(tmp_path, trace_store=None)
    effector = _TestEffector()
    orchestrator.execute(effector, kind="k", request="hello")
    # No trace_store means no traces directory created
    assert not (tmp_path / "traces").exists()


def test_execute_skips_recording_when_disabled(tmp_path: Path):
    orchestrator, trace_store = _build_orchestrator(
        tmp_path, trace_enabled=False
    )
    effector = _TestEffector()
    orchestrator.execute(effector, kind="k", request="hello")
    assert trace_store.list() == []


# ----- All status paths recorded -----


def test_records_trace_for_manual_stage(tmp_path: Path):
    orchestrator, trace_store = _build_orchestrator(
        tmp_path, initial_stage="manual"
    )
    orchestrator.execute(_TestEffector(), kind="k", request="x")
    traces = trace_store.list()
    assert len(traces) == 1
    assert traces[0].status == ActionStatus.MANUAL


def test_records_trace_for_proposed_stage(tmp_path: Path):
    orchestrator, trace_store = _build_orchestrator(
        tmp_path, initial_stage="proposed"
    )
    result = orchestrator.execute(_TestEffector(), kind="k", request="x")
    traces = trace_store.list()
    assert len(traces) == 1
    assert traces[0].status == ActionStatus.PROPOSED
    assert traces[0].plan_id == result.plan.id


def test_records_trace_for_denied_status(tmp_path: Path):
    orchestrator, trace_store = _build_orchestrator(tmp_path)
    orchestrator.execute(
        _TestEffector(gate_returns=False), kind="k", request="x"
    )
    traces = trace_store.list()
    assert traces[0].status == ActionStatus.DENIED


def test_records_trace_for_clarification(tmp_path: Path):
    orchestrator, trace_store = _build_orchestrator(
        tmp_path, clarifications=["What is X?"]
    )
    orchestrator.execute(_TestEffector(), kind="k", request="x")
    traces = trace_store.list()
    assert traces[0].status == ActionStatus.NEEDS_CLARIFICATION


# ----- Trace content -----


def test_trace_contains_dod_and_validation(tmp_path: Path):
    orchestrator, trace_store = _build_orchestrator(tmp_path)
    orchestrator.execute(_TestEffector(), kind="k", request="x")
    trace = trace_store.list()[0]
    assert len(trace.dod.criteria) == 1
    assert trace.validation is not None
    assert trace.validation.score == 1.0


def test_trace_contains_context_after_pre_load(tmp_path: Path):
    orchestrator, trace_store = _build_orchestrator(tmp_path)
    orchestrator.execute(
        _TestEffector(), kind="k", request="x", context={"input_key": "v"}
    )
    trace = trace_store.list()[0]
    assert trace.context["input_key"] == "v"
    assert trace.context["preloaded"] is True


def test_trace_provenance_uses_effector_name(tmp_path: Path):
    orchestrator, trace_store = _build_orchestrator(tmp_path)
    orchestrator.execute(_TestEffector(), kind="k", request="x")
    trace = trace_store.list()[0]
    assert trace.provenance.author == "test_effector"
    assert trace.provenance.source == "orchestrator.execute"


def test_trace_request_summary_truncated(tmp_path: Path):
    orchestrator, trace_store = _build_orchestrator(tmp_path)
    long_request = "x" * 1000
    orchestrator.execute(_TestEffector(), kind="k", request=long_request)
    trace = trace_store.list()[0]
    assert len(trace.request_summary) <= 500
    assert trace.request_summary.endswith("...")


def test_trace_records_revision_pending_in_autonomous(tmp_path: Path):
    orchestrator, trace_store = _build_orchestrator(
        tmp_path, initial_stage="autonomous"
    )
    orchestrator.execute(
        _TestEffector(act_returns={"approved": False}),
        kind="k",
        request="x",
    )
    trace = trace_store.list()[0]
    assert trace.revision_pending is True


def test_trace_round_trip_via_store(tmp_path: Path):
    orchestrator, trace_store = _build_orchestrator(tmp_path)
    orchestrator.execute(_TestEffector(), kind="k", request="x")
    written_trace = trace_store.list()[0]
    reloaded = trace_store.read(written_trace.id)
    assert reloaded == written_trace


# ----- apply_approved_plan -----


def test_apply_approved_plan_records_trace(tmp_path: Path):
    orchestrator, trace_store = _build_orchestrator(
        tmp_path, initial_stage="proposed"
    )
    effector = _TestEffector()
    propose_result = orchestrator.execute(
        effector, kind="k", request="x"
    )
    plan_id = propose_result.plan.id
    orchestrator.plan_gate.approve(plan_id, decided_by="user_a")
    orchestrator.apply_approved_plan(plan_id, effector)

    traces = trace_store.list()
    # One trace from propose, one from apply
    assert len(traces) == 2
    apply_traces = [
        t for t in traces if t.provenance.source.endswith("apply_approved_plan")
    ]
    assert len(apply_traces) == 1
    assert apply_traces[0].status == ActionStatus.APPLIED
    assert apply_traces[0].plan_id == plan_id
