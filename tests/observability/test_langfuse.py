from __future__ import annotations

from datetime import datetime, timezone

from organism.dod import DoD
from organism.lifecycle import LifecycleStage
from organism.observability import (
    LangfuseAdapter,
    LangfuseSettings,
    Trace,
)
from organism.orchestrator import ActionStatus
from organism.provenance import Provenance


def _make_trace() -> Trace:
    ts = datetime(2026, 5, 9, 10, 0, 0, tzinfo=timezone.utc)
    return Trace(
        id="trace-001",
        kind="create_entity",
        request_summary="",
        context={},
        stage=LifecycleStage.CHECKED,
        status=ActionStatus.APPLIED,
        dod=DoD(),
        started_at=ts,
        completed_at=ts,
        provenance=Provenance(author="ef", timestamp=ts),
    )


def test_default_disabled():
    adapter = LangfuseAdapter()
    assert adapter.settings.enabled is False
    adapter.post({"name": "test"})
    assert adapter.posted_spans == []


def test_enabled_post_stores_span():
    adapter = LangfuseAdapter(settings=LangfuseSettings(enabled=True))
    adapter.post({"name": "test", "trace_id": "t1"})
    assert len(adapter.posted_spans) == 1
    assert adapter.posted_spans[0]["name"] == "test"


def test_post_creates_independent_copy():
    adapter = LangfuseAdapter(settings=LangfuseSettings(enabled=True))
    span = {"name": "test", "attributes": {"k": "v"}}
    adapter.post(span)
    span["mutated"] = True
    assert "mutated" not in adapter.posted_spans[0]


def test_post_trace_converts_and_stores():
    adapter = LangfuseAdapter(settings=LangfuseSettings(enabled=True))
    adapter.post_trace(_make_trace())
    assert len(adapter.posted_spans) == 1
    span = adapter.posted_spans[0]
    assert span["name"] == "organism.execute.create_entity"
    assert span["trace_id"] == "trace-001"


def test_post_trace_silent_when_disabled():
    adapter = LangfuseAdapter(settings=LangfuseSettings(enabled=False))
    adapter.post_trace(_make_trace())
    assert adapter.posted_spans == []


def test_reset_clears_buffer():
    adapter = LangfuseAdapter(settings=LangfuseSettings(enabled=True))
    adapter.post({"name": "a"})
    adapter.post({"name": "b"})
    assert len(adapter.posted_spans) == 2
    adapter.reset()
    assert adapter.posted_spans == []


def test_flush_is_no_op():
    adapter = LangfuseAdapter(settings=LangfuseSettings(enabled=True))
    adapter.flush()  # no exception, returns None
