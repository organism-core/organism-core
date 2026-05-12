from __future__ import annotations

from datetime import datetime, timezone

from organism.dod import Criterion
from organism.lessons import Lesson
from organism.provenance import Provenance


def _sample_lesson() -> Lesson:
    return Lesson(
        id="lesson-001",
        kind="create_entity",
        observation="When entity_type is wohnbau, expect 3-15 rooms",
        provenance=Provenance(
            author="user_a",
            timestamp=datetime(2026, 5, 9, 10, 0, 0, tzinfo=timezone.utc),
            source="manual_correction",
        ),
        recorded_at=datetime(2026, 5, 9, 10, 0, 0, tzinfo=timezone.utc),
        context_pattern={"entity_type": "wohnbau"},
        criteria_hint=[
            Criterion(name="rooms_count", expected="3..15", weight=1.0),
        ],
        confidence_delta=0.1,
    )


def test_lesson_to_dict():
    lesson = _sample_lesson()
    d = lesson.to_dict()
    assert d["id"] == "lesson-001"
    assert d["kind"] == "create_entity"
    assert d["context_pattern"] == {"entity_type": "wohnbau"}
    assert d["confidence_delta"] == 0.1
    assert d["criteria_hint"][0]["name"] == "rooms_count"


def test_lesson_round_trip():
    lesson = _sample_lesson()
    restored = Lesson.from_dict(lesson.to_dict())
    assert restored == lesson


def test_lesson_from_dict_lenient_on_optional_fields():
    minimal = {
        "id": "x",
        "kind": "k",
        "observation": "obs",
        "provenance": Provenance(
            author="ef",
            timestamp=datetime(2026, 5, 9, tzinfo=timezone.utc),
        ).to_dict(),
        "recorded_at": "2026-05-09T00:00:00+00:00",
    }
    lesson = Lesson.from_dict(minimal)
    assert lesson.context_pattern == {}
    assert lesson.criteria_hint == []
    assert lesson.confidence_delta == 0.0


def test_lesson_with_empty_pattern_round_trip():
    lesson = _sample_lesson()
    lesson.context_pattern = {}
    assert Lesson.from_dict(lesson.to_dict()) == lesson
