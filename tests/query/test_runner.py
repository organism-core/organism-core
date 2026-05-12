from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from organism.observability import EventBus, QueryTraceStore
from organism.query import (
    BaseQuerier,
    QueryResult,
    QueryRunner,
    QueryRunnerSettings,
    QueryStatus,
)


class _OkQuerier(BaseQuerier):
    name = "ok_q"

    def query(self, request: Any) -> Any:
        return {"echo": request}


class _RaisingQuerier(BaseQuerier):
    name = "boom_q"

    def query(self, request: Any) -> Any:
        raise ValueError("kapow")


class _CtxQuerier(BaseQuerier):
    name = "ctx_q"

    def __init__(self) -> None:
        self.last_ctx: dict[str, Any] | None = None

    def pre_load(self, context):
        context = dict(context)
        context["enriched"] = True
        self.last_ctx = context
        return context

    def query(self, request):
        return self.last_ctx


# OK path


def test_execute_returns_ok_result_with_latency():
    runner = QueryRunner()
    res = runner.execute(_OkQuerier(), kind="k", request="hello")
    assert res.status == QueryStatus.OK
    assert res.kind == "k"
    assert res.caller == "anonymous"
    assert res.result == {"echo": "hello"}
    assert res.error == ""
    assert res.latency_ms >= 0.0
    assert res.trace_id is None  # no store wired


def test_execute_passes_caller_through():
    runner = QueryRunner()
    res = runner.execute(_OkQuerier(), kind="k", request=1, caller="http")
    assert res.caller == "http"


def test_execute_calls_pre_load_with_context():
    runner = QueryRunner()
    q = _CtxQuerier()
    res = runner.execute(q, kind="k", request="x", context={"user": "alice"})
    assert res.result == {"user": "alice", "enriched": True, "kind": "k"}


# Error path


def test_execute_catches_exception_returns_error_status():
    runner = QueryRunner()
    res = runner.execute(_RaisingQuerier(), kind="k", request="x")
    assert res.status == QueryStatus.ERROR
    assert "ValueError: kapow" in res.error
    assert res.result is None


def test_execute_records_latency_even_on_error():
    runner = QueryRunner()
    res = runner.execute(_RaisingQuerier(), kind="k", request="x")
    assert res.latency_ms >= 0.0


# Trace wiring


def test_execute_writes_trace_when_store_wired(tmp_path: Path):
    store = QueryTraceStore(tmp_path / "qtraces")
    runner = QueryRunner(trace_store=store)
    res = runner.execute(_OkQuerier(), kind="k", request="hello", caller="ui")
    assert res.trace_id is not None
    assert store.exists(res.trace_id)
    trace = store.read(res.trace_id)
    assert trace.kind == "k"
    assert trace.caller == "ui"
    assert trace.status == QueryStatus.OK


def test_execute_writes_trace_for_errors_too(tmp_path: Path):
    store = QueryTraceStore(tmp_path / "qtraces")
    runner = QueryRunner(trace_store=store)
    res = runner.execute(_RaisingQuerier(), kind="k", request="x")
    trace = store.read(res.trace_id)
    assert trace.status == QueryStatus.ERROR
    assert "kapow" in trace.error


def test_record_traces_disabled_skips_trace(tmp_path: Path):
    store = QueryTraceStore(tmp_path / "qtraces")
    runner = QueryRunner(
        trace_store=store,
        settings=QueryRunnerSettings(record_traces=False),
    )
    res = runner.execute(_OkQuerier(), kind="k", request="x")
    assert res.trace_id is None
    assert store.list() == []


def test_truncation_settings_respected(tmp_path: Path):
    store = QueryTraceStore(tmp_path / "qtraces")
    runner = QueryRunner(
        trace_store=store,
        settings=QueryRunnerSettings(
            truncate_request_repr=20, truncate_result_repr=20
        ),
    )

    class _LongQuerier(BaseQuerier):
        name = "long"

        def query(self, request):
            return "x" * 500

    runner.execute(_LongQuerier(), kind="k", request="r" * 500)
    trace = store.list()[0]
    assert len(trace.request_repr) <= 20
    assert len(trace.result_repr) <= 20


# Event emission


def test_no_event_emitted_when_emit_events_false():
    bus = EventBus()
    seen = []
    bus.subscribe_all(seen.append)
    runner = QueryRunner(event_bus=bus)
    runner.execute(_OkQuerier(), kind="k", request="x")
    assert seen == []


def test_event_emitted_when_emit_events_true_and_trace_wired(tmp_path: Path):
    bus = EventBus()
    seen = []
    bus.subscribe_all(seen.append)
    store = QueryTraceStore(tmp_path / "qtraces")
    runner = QueryRunner(
        trace_store=store,
        event_bus=bus,
        settings=QueryRunnerSettings(emit_events=True),
    )
    runner.execute(_OkQuerier(), kind="k", request="x", caller="http")
    assert len(seen) == 1
    event = seen[0]
    assert event.type == "query_recorded"
    assert event.payload["kind"] == "k"
    assert event.payload["caller"] == "http"
    assert event.payload["status"] == "ok"


def test_event_not_emitted_when_no_trace_wired_even_if_emit_events_true():
    """Without a trace store, there's no trace_id to reference, so no
    event is emitted. Settings-only enablement isn't enough."""
    bus = EventBus()
    seen = []
    bus.subscribe_all(seen.append)
    runner = QueryRunner(
        event_bus=bus, settings=QueryRunnerSettings(emit_events=True)
    )
    runner.execute(_OkQuerier(), kind="k", request="x")
    assert seen == []


# Trace store list


def test_query_trace_store_list_sorts_newest_first(tmp_path: Path):
    import time

    store = QueryTraceStore(tmp_path / "qtraces")
    runner = QueryRunner(trace_store=store)
    ids = []
    for i in range(5):
        res = runner.execute(_OkQuerier(), kind="k", request=i)
        ids.append(res.trace_id)
        # Sleep a hair so timestamps are unambiguously distinct on
        # Windows (clock resolution can be 15ms).
        time.sleep(0.02)
    listed = store.list(limit=3)
    assert len(listed) == 3
    assert listed[0].id == ids[-1]
    assert listed[1].id == ids[-2]


def test_query_trace_store_list_filters_by_kind(tmp_path: Path):
    store = QueryTraceStore(tmp_path / "qtraces")
    runner = QueryRunner(trace_store=store)
    runner.execute(_OkQuerier(), kind="kA", request=1)
    runner.execute(_OkQuerier(), kind="kB", request=2)
    runner.execute(_OkQuerier(), kind="kA", request=3)
    assert len(store.list(kind="kA")) == 2
    assert len(store.list(kind="kB")) == 1
