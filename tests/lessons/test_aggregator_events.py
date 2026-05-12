from __future__ import annotations

from pathlib import Path

from organism.lessons import LessonsAggregator, LessonsStore
from organism.lessons.aggregator import EVENT_LESSON_RECORDED
from organism.observability import Event, EventBus


def _build(tmp_path: Path) -> tuple[LessonsAggregator, list[Event]]:
    bus = EventBus()
    received: list[Event] = []
    bus.subscribe_all(lambda e: received.append(e))
    aggregator = LessonsAggregator(
        store=LessonsStore(tmp_path / "lessons"),
        event_bus=bus,
    )
    return aggregator, received


def test_record_lesson_publishes_event(tmp_path: Path):
    aggregator, received = _build(tmp_path)
    lesson = aggregator.record_lesson(
        kind="k",
        observation="hi",
    )
    events = [e for e in received if e.type == EVENT_LESSON_RECORDED]
    assert len(events) == 1
    assert events[0].payload == {
        "lesson_id": lesson.id,
        "kind": "k",
        "observation": "hi",
    }


def test_event_provenance_from_aggregator(tmp_path: Path):
    aggregator, received = _build(tmp_path)
    aggregator.record_lesson(kind="k", observation="o")
    events = [e for e in received if e.type == EVENT_LESSON_RECORDED]
    assert events[0].provenance.author == "lessons_aggregator"
    assert events[0].provenance.source == EVENT_LESSON_RECORDED


def test_no_bus_silent(tmp_path: Path):
    aggregator = LessonsAggregator(store=LessonsStore(tmp_path / "lessons"))
    # No exception
    lesson = aggregator.record_lesson(kind="k", observation="o")
    assert lesson.id


def test_subscribe_only_lesson_recorded(tmp_path: Path):
    bus = EventBus()
    received: list[Event] = []
    bus.subscribe(EVENT_LESSON_RECORDED, lambda e: received.append(e))
    aggregator = LessonsAggregator(
        store=LessonsStore(tmp_path / "lessons"),
        event_bus=bus,
    )
    aggregator.record_lesson(kind="k", observation="o")
    aggregator.record_lesson(kind="k2", observation="o2")
    assert len(received) == 2
