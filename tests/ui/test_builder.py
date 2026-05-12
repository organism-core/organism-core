from __future__ import annotations

from pathlib import Path

import pytest

from organism.dod import DoDEngine
from organism.lessons import LessonsAggregator, LessonsStore
from organism.lifecycle import (
    LifecycleManager,
    LifecycleSettings,
    LifecycleStore,
)
from organism.observability import QueryTraceStore
from organism.plan_gate import PlanGate, PlanStore
from organism.ui import (
    Cockpit,
    CockpitBuilder,
    CockpitBuilderError,
    CockpitSettings,
)


def _stack(tmp_path: Path):
    engine = DoDEngine(sources=[])
    plan_gate = PlanGate(store=PlanStore(tmp_path / "plans"))
    lifecycle = LifecycleManager(
        store=LifecycleStore(tmp_path / "lifecycle"),
        settings=LifecycleSettings(initial_stage="proposed"),
    )
    lessons = LessonsAggregator(store=LessonsStore(tmp_path / "lessons"))
    return engine, plan_gate, lifecycle, lessons


def test_builder_returns_cockpit_when_required_set(tmp_path: Path):
    engine, gate, lifecycle, lessons = _stack(tmp_path)
    cockpit = (
        CockpitBuilder()
        .with_engine(engine)
        .with_plan_gate(gate)
        .with_lifecycle(lifecycle)
        .with_lessons(lessons)
        .build()
    )
    assert isinstance(cockpit, Cockpit)
    assert cockpit.engine is engine
    assert cockpit.plan_gate is gate
    assert cockpit.lifecycle is lifecycle
    assert cockpit.lessons is lessons
    assert cockpit.query_trace_store is None


def test_builder_attaches_optional_query_trace_store(tmp_path: Path):
    engine, gate, lifecycle, lessons = _stack(tmp_path)
    qstore = QueryTraceStore(tmp_path / "qtraces")
    cockpit = (
        CockpitBuilder()
        .with_engine(engine)
        .with_plan_gate(gate)
        .with_lifecycle(lifecycle)
        .with_lessons(lessons)
        .with_query_trace_store(qstore)
        .build()
    )
    assert cockpit.query_trace_store is qstore


def test_builder_attaches_optional_settings(tmp_path: Path):
    engine, gate, lifecycle, lessons = _stack(tmp_path)
    settings = CockpitSettings(plan_list_max_items=5)
    cockpit = (
        CockpitBuilder()
        .with_engine(engine)
        .with_plan_gate(gate)
        .with_lifecycle(lifecycle)
        .with_lessons(lessons)
        .with_settings(settings)
        .build()
    )
    assert cockpit.settings is settings


def test_builder_raises_when_engine_missing(tmp_path: Path):
    _, gate, lifecycle, lessons = _stack(tmp_path)
    with pytest.raises(CockpitBuilderError, match="engine"):
        (
            CockpitBuilder()
            .with_plan_gate(gate)
            .with_lifecycle(lifecycle)
            .with_lessons(lessons)
            .build()
        )


def test_builder_raises_when_all_required_missing():
    with pytest.raises(CockpitBuilderError) as exc:
        CockpitBuilder().build()
    msg = str(exc.value)
    assert "engine" in msg
    assert "plan_gate" in msg
    assert "lifecycle" in msg
    assert "lessons" in msg


def test_builder_with_query_trace_store_none_explicitly(tmp_path: Path):
    engine, gate, lifecycle, lessons = _stack(tmp_path)
    cockpit = (
        CockpitBuilder()
        .with_engine(engine)
        .with_plan_gate(gate)
        .with_lifecycle(lifecycle)
        .with_lessons(lessons)
        .with_query_trace_store(None)
        .build()
    )
    assert cockpit.query_trace_store is None


def test_builder_supports_repeat_build_returning_fresh_cockpits(tmp_path: Path):
    engine, gate, lifecycle, lessons = _stack(tmp_path)
    builder = (
        CockpitBuilder()
        .with_engine(engine)
        .with_plan_gate(gate)
        .with_lifecycle(lifecycle)
        .with_lessons(lessons)
    )
    c1 = builder.build()
    c2 = builder.build()
    assert c1 is not c2
    assert c1.engine is c2.engine  # same wiring, distinct instances
