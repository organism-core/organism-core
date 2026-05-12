from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from organism.dod import DoD
from organism.lifecycle import LifecycleStage
from organism.observability import TRACE_FILE_SUFFIX, Trace, TraceStore
from organism.orchestrator import ActionStatus
from organism.provenance import Provenance


def _make_trace(
    trace_id: str = "t1",
    kind: str = "create_entity",
    status: ActionStatus = ActionStatus.APPLIED,
) -> Trace:
    ts = datetime(2026, 5, 9, 10, 0, 0, tzinfo=timezone.utc)
    return Trace(
        id=trace_id,
        kind=kind,
        request_summary="'x'",
        context={},
        stage=LifecycleStage.CHECKED,
        status=status,
        dod=DoD(),
        started_at=ts,
        completed_at=ts,
        provenance=Provenance(author="ef", timestamp=ts),
    )


def test_write_creates_file(tmp_path: Path):
    store = TraceStore(tmp_path)
    store.write(_make_trace(trace_id="t1"))
    expected = tmp_path / f"t1{TRACE_FILE_SUFFIX}"
    assert expected.exists()


def test_round_trip(tmp_path: Path):
    store = TraceStore(tmp_path)
    trace = _make_trace(trace_id="t1")
    store.write(trace)
    loaded = store.read("t1")
    assert loaded == trace


def test_read_missing_raises(tmp_path: Path):
    store = TraceStore(tmp_path)
    with pytest.raises(FileNotFoundError, match="Trace 'ghost' not found"):
        store.read("ghost")


def test_exists(tmp_path: Path):
    store = TraceStore(tmp_path)
    assert not store.exists("t1")
    store.write(_make_trace(trace_id="t1"))
    assert store.exists("t1")


def test_list_empty(tmp_path: Path):
    assert TraceStore(tmp_path).list() == []


def test_list_missing_root(tmp_path: Path):
    assert TraceStore(tmp_path / "missing").list() == []


def test_list_all(tmp_path: Path):
    store = TraceStore(tmp_path)
    store.write(_make_trace(trace_id="t1", kind="ka"))
    store.write(_make_trace(trace_id="t2", kind="kb"))
    assert {t.id for t in store.list()} == {"t1", "t2"}


def test_list_filters_by_kind(tmp_path: Path):
    store = TraceStore(tmp_path)
    store.write(_make_trace(trace_id="t1", kind="ka"))
    store.write(_make_trace(trace_id="t2", kind="kb"))
    store.write(_make_trace(trace_id="t3", kind="ka"))
    assert {t.id for t in store.list(kind="ka")} == {"t1", "t3"}


def test_list_filters_by_status(tmp_path: Path):
    store = TraceStore(tmp_path)
    store.write(_make_trace(trace_id="t1", status=ActionStatus.APPLIED))
    store.write(_make_trace(trace_id="t2", status=ActionStatus.DENIED))
    store.write(_make_trace(trace_id="t3", status=ActionStatus.APPLIED))
    assert {t.id for t in store.list(status=ActionStatus.APPLIED)} == {
        "t1",
        "t3",
    }


def test_write_overwrites(tmp_path: Path):
    store = TraceStore(tmp_path)
    store.write(_make_trace(trace_id="t1", status=ActionStatus.APPLIED))
    store.write(_make_trace(trace_id="t1", status=ActionStatus.DENIED))
    loaded = store.read("t1")
    assert loaded.status == ActionStatus.DENIED
