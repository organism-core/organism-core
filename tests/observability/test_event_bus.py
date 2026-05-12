from __future__ import annotations

from datetime import datetime, timezone

import pytest

from organism.observability import Event, EventBus, EventBusSettings
from organism.provenance import Provenance


def test_event_now_creates_with_current_timestamp():
    event = Event.now("test_event", payload={"x": 1})
    assert event.type == "test_event"
    assert event.payload == {"x": 1}
    assert (
        datetime.now(timezone.utc) - event.timestamp
    ).total_seconds() < 5


def test_event_round_trip_with_provenance():
    prov = Provenance(
        author="ef",
        timestamp=datetime(2026, 5, 9, tzinfo=timezone.utc),
    )
    event = Event(
        type="t",
        payload={"k": "v"},
        timestamp=datetime(2026, 5, 9, tzinfo=timezone.utc),
        provenance=prov,
    )
    restored = Event.from_dict(event.to_dict())
    assert restored == event


def test_event_round_trip_without_provenance():
    event = Event.now("t", payload={"k": 1})
    restored = Event.from_dict(event.to_dict())
    assert restored == event


def test_subscribe_and_publish():
    bus = EventBus()
    received: list[Event] = []
    bus.subscribe("test", lambda e: received.append(e))
    bus.publish(Event.now("test", payload={"x": 1}))
    assert len(received) == 1
    assert received[0].payload == {"x": 1}


def test_publish_only_to_matching_subscribers():
    bus = EventBus()
    a_calls: list[Event] = []
    b_calls: list[Event] = []
    bus.subscribe("a", lambda e: a_calls.append(e))
    bus.subscribe("b", lambda e: b_calls.append(e))
    bus.publish(Event.now("a", payload={"x": 1}))
    assert len(a_calls) == 1
    assert b_calls == []


def test_subscribe_all_receives_every_event():
    bus = EventBus()
    received: list[Event] = []
    bus.subscribe_all(lambda e: received.append(e))
    bus.publish(Event.now("a"))
    bus.publish(Event.now("b"))
    assert [e.type for e in received] == ["a", "b"]


def test_targeted_and_wildcard_both_fire():
    bus = EventBus()
    targeted: list[Event] = []
    wildcard: list[Event] = []
    bus.subscribe("a", lambda e: targeted.append(e))
    bus.subscribe_all(lambda e: wildcard.append(e))
    bus.publish(Event.now("a"))
    assert len(targeted) == 1
    assert len(wildcard) == 1


def test_unsubscribe_removes_handler():
    bus = EventBus()
    received: list[Event] = []
    sub_id = bus.subscribe("a", lambda e: received.append(e))
    bus.unsubscribe(sub_id)
    bus.publish(Event.now("a"))
    assert received == []


def test_unsubscribe_wildcard():
    bus = EventBus()
    received: list[Event] = []
    sub_id = bus.subscribe_all(lambda e: received.append(e))
    bus.unsubscribe(sub_id)
    bus.publish(Event.now("a"))
    assert received == []


def test_unsubscribe_unknown_id_is_silent():
    bus = EventBus()
    bus.unsubscribe("never_existed")  # should not raise


def test_disabled_bus_does_not_publish():
    bus = EventBus(settings=EventBusSettings(enabled=False))
    received: list[Event] = []
    bus.subscribe("a", lambda e: received.append(e))
    bus.publish(Event.now("a"))
    assert received == []


def test_handler_error_continue_default():
    bus = EventBus()
    received: list[Event] = []

    def boom(e):
        raise RuntimeError("boom")

    bus.subscribe("a", boom)
    bus.subscribe("a", lambda e: received.append(e))
    bus.publish(Event.now("a"))
    # second handler still fired
    assert len(received) == 1


def test_handler_error_raise_propagates():
    bus = EventBus(
        settings=EventBusSettings(handler_error_action="raise")
    )

    def boom(e):
        raise RuntimeError("boom")

    bus.subscribe("a", boom)
    with pytest.raises(RuntimeError, match="boom"):
        bus.publish(Event.now("a"))


def test_subscribe_multiple_handlers_for_same_type():
    bus = EventBus()
    a: list[Event] = []
    b: list[Event] = []
    bus.subscribe("t", lambda e: a.append(e))
    bus.subscribe("t", lambda e: b.append(e))
    bus.publish(Event.now("t"))
    assert len(a) == 1
    assert len(b) == 1


def test_unique_subscription_ids():
    bus = EventBus()
    id1 = bus.subscribe("a", lambda e: None)
    id2 = bus.subscribe("a", lambda e: None)
    id3 = bus.subscribe_all(lambda e: None)
    assert len({id1, id2, id3}) == 3
