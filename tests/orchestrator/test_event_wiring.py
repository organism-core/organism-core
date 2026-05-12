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
from organism.observability import Event, EventBus, TraceStore
from organism.orchestrator import (
    ActionOrchestrator,
    ActionStatus,
)
from organism.orchestrator.orchestrator import (
    EVENT_LIFECYCLE_TRANSITION,
    EVENT_PLAN_PROPOSED,
    EVENT_TRACE_RECORDED,
)
from organism.plan_gate import PlanGate, PlanStore


class _Source:
    def __init__(self, criteria, clarifications=None):
        self.name = "src"
        self._criteria = criteria
        self._clarifications = clarifications or []

    def contribute(self, request, context, current):
        return SourceContribution(
            source_name=self.name,
            criteria=[
                Criterion(name=c.name, expected=c.expected, weight=c.weight)
                for c in self._criteria
            ],
            confidence_delta=1.0,
            clarifications=list(self._clarifications),
        )


class _Effector:
    name = "ef"

    def __init__(self, result_value: Any = None):
        self.result_value = (
            result_value if result_value is not None else {"approved": True}
        )

    def pre_load(self, ctx):
        return ctx

    def define_done(self, request, context):
        return {}

    def act(self, request):
        return self.result_value

    def upstream(self, kind, payload):
        pass

    def gate(self, action):
        return True


def _build(
    tmp_path: Path,
    *,
    initial_stage: str = "checked",
    criteria=None,
    with_trace: bool = True,
) -> tuple[ActionOrchestrator, EventBus, list[Event]]:
    bus = EventBus()
    received: list[Event] = []
    bus.subscribe_all(lambda e: received.append(e))

    source = _Source(
        criteria=criteria or [Criterion(name="approved", expected=True)],
    )
    engine = DoDEngine(sources=[source])
    validator = DoDValidator()
    plan_gate = PlanGate(store=PlanStore(tmp_path / "plans"))
    lifecycle = LifecycleManager(
        store=LifecycleStore(tmp_path / "lifecycle"),
        settings=LifecycleSettings(initial_stage=initial_stage),
    )
    trace_store = TraceStore(tmp_path / "traces") if with_trace else None
    orchestrator = ActionOrchestrator(
        engine=engine,
        validator=validator,
        plan_gate=plan_gate,
        lifecycle=lifecycle,
        trace_store=trace_store,
        event_bus=bus,
    )
    return orchestrator, bus, received


# Plan-proposed


def test_plan_proposed_event_fires(tmp_path: Path):
    orchestrator, _, received = _build(
        tmp_path, initial_stage="proposed"
    )
    result = orchestrator.execute(_Effector(), kind="k", request="x")
    plan_events = [e for e in received if e.type == EVENT_PLAN_PROPOSED]
    assert len(plan_events) == 1
    assert plan_events[0].payload["plan_id"] == result.plan.id
    assert plan_events[0].payload["kind"] == "k"
    assert plan_events[0].payload["proposed_by"] == "ef"


def test_plan_proposed_not_fired_for_checked_stage(tmp_path: Path):
    orchestrator, _, received = _build(
        tmp_path, initial_stage="checked"
    )
    orchestrator.execute(_Effector(), kind="k", request="x")
    assert not any(
        e.type == EVENT_PLAN_PROPOSED for e in received
    )


# Trace-recorded


def test_trace_recorded_event_fires_on_execute(tmp_path: Path):
    orchestrator, _, received = _build(tmp_path)
    orchestrator.execute(_Effector(), kind="k", request="x")
    trace_events = [e for e in received if e.type == EVENT_TRACE_RECORDED]
    assert len(trace_events) == 1
    assert trace_events[0].payload["kind"] == "k"
    assert trace_events[0].payload["status"] == "applied"


def test_trace_recorded_not_fired_when_no_trace_store(tmp_path: Path):
    orchestrator, _, received = _build(tmp_path, with_trace=False)
    orchestrator.execute(_Effector(), kind="k", request="x")
    assert not any(
        e.type == EVENT_TRACE_RECORDED for e in received
    )


def test_trace_recorded_event_for_apply_approved_plan(tmp_path: Path):
    orchestrator, _, received = _build(
        tmp_path, initial_stage="proposed"
    )
    propose_result = orchestrator.execute(
        _Effector(), kind="k", request="x"
    )
    received.clear()  # clear propose-side events

    orchestrator.plan_gate.approve(
        propose_result.plan.id, decided_by="user_a"
    )
    orchestrator.apply_approved_plan(
        propose_result.plan.id, _Effector()
    )
    trace_events = [e for e in received if e.type == EVENT_TRACE_RECORDED]
    assert len(trace_events) == 1
    assert trace_events[0].payload["kind"] == "k"


# Lifecycle-transition


def test_lifecycle_transition_event_fires(tmp_path: Path):
    # Setup: short promote_after_n + immediate promotion
    bus = EventBus()
    received: list[Event] = []
    bus.subscribe_all(lambda e: received.append(e))

    source = _Source(criteria=[Criterion(name="approved", expected=True)])
    engine = DoDEngine(sources=[source])
    plan_gate = PlanGate(store=PlanStore(tmp_path / "plans"))
    lifecycle = LifecycleManager(
        store=LifecycleStore(tmp_path / "lifecycle"),
        settings=LifecycleSettings(
            initial_stage="checked",
            promote_after_n=1,
            promote_score_threshold=0.5,
            window_size=10,
        ),
    )
    orchestrator = ActionOrchestrator(
        engine=engine,
        validator=DoDValidator(),
        plan_gate=plan_gate,
        lifecycle=lifecycle,
        event_bus=bus,
    )

    orchestrator.execute(_Effector(), kind="k", request="x")
    transition_events = [
        e for e in received if e.type == EVENT_LIFECYCLE_TRANSITION
    ]
    assert len(transition_events) == 1
    assert transition_events[0].payload["kind"] == "k"
    assert transition_events[0].payload["from_stage"] == "checked"
    assert transition_events[0].payload["to_stage"] == "routine"


def test_lifecycle_transition_not_fired_without_transition(tmp_path: Path):
    orchestrator, _, received = _build(tmp_path)
    orchestrator.execute(_Effector(), kind="k", request="x")
    transition_events = [
        e for e in received if e.type == EVENT_LIFECYCLE_TRANSITION
    ]
    assert transition_events == []


# Provenance on events


def test_event_has_provenance_from_orchestrator(tmp_path: Path):
    orchestrator, _, received = _build(tmp_path)
    orchestrator.execute(_Effector(), kind="k", request="x")
    trace_events = [e for e in received if e.type == EVENT_TRACE_RECORDED]
    assert trace_events[0].provenance.author == "orchestrator"
    assert trace_events[0].provenance.source == EVENT_TRACE_RECORDED


# No event_bus = no crash


def test_no_event_bus_silent(tmp_path: Path):
    source = _Source(criteria=[Criterion(name="approved", expected=True)])
    engine = DoDEngine(sources=[source])
    plan_gate = PlanGate(store=PlanStore(tmp_path / "plans"))
    lifecycle = LifecycleManager(
        store=LifecycleStore(tmp_path / "lifecycle"),
        settings=LifecycleSettings(initial_stage="checked"),
    )
    orchestrator = ActionOrchestrator(
        engine=engine,
        validator=DoDValidator(),
        plan_gate=plan_gate,
        lifecycle=lifecycle,
        # no event_bus
    )
    # Should not raise
    result = orchestrator.execute(_Effector(), kind="k", request="x")
    assert result.status == ActionStatus.APPLIED


# Order: plan_proposed before trace_recorded for PROPOSED


def test_event_order_for_proposed(tmp_path: Path):
    orchestrator, _, received = _build(
        tmp_path, initial_stage="proposed"
    )
    orchestrator.execute(_Effector(), kind="k", request="x")
    types_in_order = [e.type for e in received]
    plan_idx = types_in_order.index(EVENT_PLAN_PROPOSED)
    trace_idx = types_in_order.index(EVENT_TRACE_RECORDED)
    assert plan_idx < trace_idx
