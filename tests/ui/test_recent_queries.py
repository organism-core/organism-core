from __future__ import annotations

from pathlib import Path

from organism.dod import DoDEngine
from organism.lessons import LessonsAggregator, LessonsStore
from organism.lifecycle import (
    LifecycleManager,
    LifecycleSettings,
    LifecycleStore,
)
from organism.observability import QueryTraceStore
from organism.plan_gate import PlanGate, PlanStore
from organism.query import BaseQuerier, QueryRunner
from organism.ui import CockpitBuilder


class _StubQuerier(BaseQuerier):
    name = "stub"

    def query(self, request):
        return {"echo": request}


def _build_cockpit(tmp_path: Path, *, with_qstore: bool = True):
    qstore = QueryTraceStore(tmp_path / "qtraces") if with_qstore else None
    cockpit = (
        CockpitBuilder()
        .with_engine(DoDEngine(sources=[]))
        .with_plan_gate(PlanGate(store=PlanStore(tmp_path / "plans")))
        .with_lifecycle(
            LifecycleManager(
                store=LifecycleStore(tmp_path / "lifecycle"),
                settings=LifecycleSettings(initial_stage="proposed"),
            )
        )
        .with_lessons(
            LessonsAggregator(store=LessonsStore(tmp_path / "lessons"))
        )
        .with_query_trace_store(qstore)
        .build()
    )
    return cockpit, qstore


def test_recent_queries_empty_when_no_store_wired(tmp_path: Path):
    cockpit, _ = _build_cockpit(tmp_path, with_qstore=False)
    assert cockpit.recent_queries() == []


def test_recent_queries_returns_view_per_trace(tmp_path: Path):
    cockpit, qstore = _build_cockpit(tmp_path)
    runner = QueryRunner(trace_store=qstore)
    for r in ("a", "b", "c"):
        runner.execute(_StubQuerier(), kind="k", request=r, caller="ui")
    views = cockpit.recent_queries()
    assert len(views) == 3
    for v in views:
        assert v.kind == "k"
        assert v.caller == "ui"
        assert v.status == "ok"
        assert v.latency_ms >= 0.0


def test_recent_queries_filters_by_kind(tmp_path: Path):
    cockpit, qstore = _build_cockpit(tmp_path)
    runner = QueryRunner(trace_store=qstore)
    runner.execute(_StubQuerier(), kind="alpha", request="a")
    runner.execute(_StubQuerier(), kind="beta", request="b")
    runner.execute(_StubQuerier(), kind="alpha", request="c")
    alphas = cockpit.recent_queries(kind="alpha")
    assert {v.kind for v in alphas} == {"alpha"}
    assert len(alphas) == 2


def test_recent_queries_respects_limit(tmp_path: Path):
    cockpit, qstore = _build_cockpit(tmp_path)
    runner = QueryRunner(trace_store=qstore)
    for _ in range(5):
        runner.execute(_StubQuerier(), kind="k", request="x")
    assert len(cockpit.recent_queries(limit=2)) == 2
