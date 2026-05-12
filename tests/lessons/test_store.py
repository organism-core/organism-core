from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from organism.lessons import LESSON_FILE_SUFFIX, Lesson, LessonsStore
from organism.provenance import Provenance


def _make_lesson(
    lesson_id: str = "L1",
    kind: str = "create_entity",
) -> Lesson:
    ts = datetime(2026, 5, 9, 10, 0, 0, tzinfo=timezone.utc)
    return Lesson(
        id=lesson_id,
        kind=kind,
        observation="obs",
        provenance=Provenance(author="ef", timestamp=ts),
        recorded_at=ts,
    )


def test_write_creates_file_under_kind(tmp_path: Path):
    store = LessonsStore(tmp_path)
    store.write(_make_lesson(lesson_id="L1", kind="ka"))
    expected = tmp_path / "ka" / f"L1{LESSON_FILE_SUFFIX}"
    assert expected.exists()


def test_round_trip(tmp_path: Path):
    store = LessonsStore(tmp_path)
    lesson = _make_lesson(lesson_id="L1")
    store.write(lesson)
    assert store.read("L1") == lesson


def test_read_missing_raises(tmp_path: Path):
    store = LessonsStore(tmp_path)
    with pytest.raises(FileNotFoundError, match="Lesson 'ghost' not found"):
        store.read("ghost")


def test_read_walks_kinds(tmp_path: Path):
    store = LessonsStore(tmp_path)
    store.write(_make_lesson(lesson_id="L1", kind="ka"))
    store.write(_make_lesson(lesson_id="L2", kind="kb"))
    assert store.read("L1").kind == "ka"
    assert store.read("L2").kind == "kb"


def test_exists(tmp_path: Path):
    store = LessonsStore(tmp_path)
    assert not store.exists("L1")
    store.write(_make_lesson(lesson_id="L1"))
    assert store.exists("L1")


def test_list_empty_root(tmp_path: Path):
    assert LessonsStore(tmp_path).list() == []


def test_list_missing_root(tmp_path: Path):
    assert LessonsStore(tmp_path / "missing").list() == []


def test_list_filters_by_kind(tmp_path: Path):
    store = LessonsStore(tmp_path)
    store.write(_make_lesson(lesson_id="L1", kind="ka"))
    store.write(_make_lesson(lesson_id="L2", kind="kb"))
    store.write(_make_lesson(lesson_id="L3", kind="ka"))
    assert {l.id for l in store.list(kind="ka")} == {"L1", "L3"}


def test_list_unknown_kind_returns_empty(tmp_path: Path):
    store = LessonsStore(tmp_path)
    store.write(_make_lesson(lesson_id="L1", kind="ka"))
    assert store.list(kind="ghost") == []
