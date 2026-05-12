from __future__ import annotations

from organism.observability.event_bus import Event
from organism.ui.events import (
    EVENT_QUERY_RECORDED,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    UIEvent,
)


def test_query_recorded_ok_is_info():
    e = Event.now(
        type=EVENT_QUERY_RECORDED,
        payload={
            "kind": "k",
            "caller": "ui",
            "status": "ok",
            "latency_ms": 12.3,
            "trace_id": "t-1",
        },
    )
    ui = UIEvent.from_bus_event(e)
    assert ui.severity == SEVERITY_INFO
    assert "kind=k" in ui.summary
    assert "caller=ui" in ui.summary
    assert "status=ok" in ui.summary
    assert "12.3ms" in ui.summary


def test_query_recorded_error_is_warning():
    e = Event.now(
        type=EVENT_QUERY_RECORDED,
        payload={
            "kind": "k",
            "caller": "ui",
            "status": "error",
            "latency_ms": 0.5,
            "trace_id": "t-1",
        },
    )
    ui = UIEvent.from_bus_event(e)
    assert ui.severity == SEVERITY_WARNING
    assert "status=error" in ui.summary
