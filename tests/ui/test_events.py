from __future__ import annotations

from organism.observability.event_bus import Event, EventBus
from organism.ui.events import (
    EVENT_LESSON_RECORDED,
    EVENT_LIFECYCLE_TRANSITION,
    EVENT_PLAN_PROPOSED,
    EVENT_TRACE_RECORDED,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    UIEvent,
    UIEventStream,
)


# ---------- UIEvent.from_bus_event


def test_plan_proposed_is_info_severity():
    e = Event.now(
        type=EVENT_PLAN_PROPOSED,
        payload={"kind": "k1", "proposed_by": "ef"},
    )
    ui = UIEvent.from_bus_event(e)
    assert ui.type == EVENT_PLAN_PROPOSED
    assert ui.kind == "k1"
    assert ui.severity == SEVERITY_INFO
    assert "ef" in ui.summary


def test_plan_proposed_revision_escalation_is_warning():
    e = Event.now(
        type=EVENT_PLAN_PROPOSED,
        payload={
            "kind": "k1",
            "proposed_by": "orchestrator:revision_escalation",
        },
    )
    ui = UIEvent.from_bus_event(e)
    assert ui.severity == SEVERITY_WARNING
    assert "revision escalation" in ui.summary


def test_lifecycle_transition_promote_is_info():
    e = Event.now(
        type=EVENT_LIFECYCLE_TRANSITION,
        payload={
            "kind": "k1",
            "from_stage": "checked",
            "to_stage": "routine",
            "reason": "promote: avg ...",
        },
    )
    ui = UIEvent.from_bus_event(e)
    assert ui.severity == SEVERITY_INFO
    assert "checked -> routine" in ui.summary


def test_lifecycle_transition_demote_is_warning():
    e = Event.now(
        type=EVENT_LIFECYCLE_TRANSITION,
        payload={
            "kind": "k1",
            "from_stage": "routine",
            "to_stage": "checked",
            "reason": "demote: avg ...",
        },
    )
    ui = UIEvent.from_bus_event(e)
    assert ui.severity == SEVERITY_WARNING


def test_lesson_recorded_includes_truncated_observation():
    e = Event.now(
        type=EVENT_LESSON_RECORDED,
        payload={"kind": "k1", "observation": "x" * 200, "lesson_id": "L"},
    )
    ui = UIEvent.from_bus_event(e)
    # 60-char truncation + ellipsis
    assert len(ui.summary) < 200


def test_trace_recorded_denied_status_is_warning():
    e = Event.now(
        type=EVENT_TRACE_RECORDED,
        payload={"kind": "k1", "status": "denied", "trace_id": "T"},
    )
    ui = UIEvent.from_bus_event(e)
    assert ui.severity == SEVERITY_WARNING


def test_trace_recorded_applied_status_is_info():
    e = Event.now(
        type=EVENT_TRACE_RECORDED,
        payload={"kind": "k1", "status": "applied", "trace_id": "T"},
    )
    ui = UIEvent.from_bus_event(e)
    assert ui.severity == SEVERITY_INFO


def test_unknown_event_type_falls_back_to_info():
    e = Event.now(type="custom_event", payload={"kind": "k1"})
    ui = UIEvent.from_bus_event(e)
    assert ui.severity == SEVERITY_INFO
    assert "custom_event" in ui.summary


def test_ui_event_to_dict_returns_serializable():
    e = Event.now(
        type=EVENT_PLAN_PROPOSED, payload={"kind": "k1", "proposed_by": "ef"}
    )
    d = UIEvent.from_bus_event(e).to_dict()
    assert d["type"] == EVENT_PLAN_PROPOSED
    assert d["kind"] == "k1"


# ---------- UIEventStream


def test_stream_relays_bus_events_to_subscribers():
    bus = EventBus()
    stream = UIEventStream(bus)
    received: list[UIEvent] = []
    stream.subscribe(None, received.append)

    bus.publish(
        Event.now(type=EVENT_PLAN_PROPOSED, payload={"kind": "k1"})
    )
    bus.publish(
        Event.now(type=EVENT_LESSON_RECORDED, payload={"kind": "k1"})
    )
    assert [e.type for e in received] == [
        EVENT_PLAN_PROPOSED,
        EVENT_LESSON_RECORDED,
    ]


def test_stream_subscribe_with_filter_only_delivers_matching_types():
    bus = EventBus()
    stream = UIEventStream(bus)
    received: list[UIEvent] = []
    stream.subscribe([EVENT_PLAN_PROPOSED], received.append)

    bus.publish(
        Event.now(type=EVENT_PLAN_PROPOSED, payload={"kind": "k1"})
    )
    bus.publish(
        Event.now(type=EVENT_LESSON_RECORDED, payload={"kind": "k1"})
    )
    assert [e.type for e in received] == [EVENT_PLAN_PROPOSED]


def test_stream_unsubscribe_stops_delivery():
    bus = EventBus()
    stream = UIEventStream(bus)
    received: list[UIEvent] = []
    sub_id = stream.subscribe(None, received.append)
    bus.publish(Event.now(type=EVENT_PLAN_PROPOSED, payload={"kind": "k1"}))
    assert len(received) == 1

    stream.unsubscribe(sub_id)
    bus.publish(Event.now(type=EVENT_PLAN_PROPOSED, payload={"kind": "k1"}))
    assert len(received) == 1


def test_stream_close_detaches_from_bus():
    bus = EventBus()
    stream = UIEventStream(bus)
    received: list[UIEvent] = []
    stream.subscribe(None, received.append)
    stream.close()
    bus.publish(Event.now(type=EVENT_PLAN_PROPOSED, payload={"kind": "k1"}))
    assert received == []


def test_stream_swallows_handler_exceptions():
    bus = EventBus()
    stream = UIEventStream(bus)
    received: list[UIEvent] = []

    def bad(_event):
        raise RuntimeError("crash")

    stream.subscribe(None, bad)
    stream.subscribe(None, received.append)
    # Should not raise; second handler still gets called.
    bus.publish(Event.now(type=EVENT_PLAN_PROPOSED, payload={"kind": "k1"}))
    assert len(received) == 1


def test_stream_multiple_subscribers_each_receive_event():
    bus = EventBus()
    stream = UIEventStream(bus)
    a: list[UIEvent] = []
    b: list[UIEvent] = []
    stream.subscribe(None, a.append)
    stream.subscribe(None, b.append)
    bus.publish(Event.now(type=EVENT_PLAN_PROPOSED, payload={"kind": "k1"}))
    assert len(a) == 1
    assert len(b) == 1
