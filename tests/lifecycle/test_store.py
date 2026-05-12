from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from organism.lifecycle import (
    LIFECYCLE_FILE_SUFFIX,
    ActionOutcome,
    LifecycleStage,
    LifecycleState,
    LifecycleStore,
)


def _make_state(
    kind: str = "my_kind",
    stage: LifecycleStage = LifecycleStage.PROPOSED,
) -> LifecycleState:
    return LifecycleState(kind=kind, stage=stage)


def test_write_creates_file(tmp_path: Path):
    store = LifecycleStore(tmp_path)
    store.write(_make_state(kind="my_kind"))
    expected = tmp_path / f"my_kind{LIFECYCLE_FILE_SUFFIX}"
    assert expected.exists()


def test_read_round_trip(tmp_path: Path):
    store = LifecycleStore(tmp_path)
    state = _make_state(kind="x")
    store.write(state)
    assert store.read("x") == state


def test_read_missing_raises(tmp_path: Path):
    store = LifecycleStore(tmp_path)
    with pytest.raises(FileNotFoundError, match="kind 'ghost' not found"):
        store.read("ghost")


def test_exists(tmp_path: Path):
    store = LifecycleStore(tmp_path)
    assert not store.exists("a")
    store.write(_make_state(kind="a"))
    assert store.exists("a")
    assert not store.exists("b")


def test_list_kinds_empty(tmp_path: Path):
    assert LifecycleStore(tmp_path).list_kinds() == []


def test_list_kinds_missing_root(tmp_path: Path):
    assert LifecycleStore(tmp_path / "missing").list_kinds() == []


def test_list_kinds_sorted(tmp_path: Path):
    store = LifecycleStore(tmp_path)
    store.write(_make_state(kind="zeta"))
    store.write(_make_state(kind="alpha"))
    store.write(_make_state(kind="mike"))
    assert store.list_kinds() == ["alpha", "mike", "zeta"]


def test_round_trip_preserves_outcomes_and_history(tmp_path: Path):
    store = LifecycleStore(tmp_path)
    state = LifecycleState(
        kind="x",
        stage=LifecycleStage.CHECKED,
        recent_outcomes=[
            ActionOutcome(
                plan_id="p1",
                score=0.95,
                recorded_at=datetime(
                    2026, 5, 9, 10, 0, 0, tzinfo=timezone.utc
                ),
            ),
        ],
    )
    store.write(state)
    loaded = store.read("x")
    assert loaded == state


def test_write_overwrites_existing(tmp_path: Path):
    store = LifecycleStore(tmp_path)
    store.write(_make_state(kind="x", stage=LifecycleStage.PROPOSED))
    store.write(_make_state(kind="x", stage=LifecycleStage.CHECKED))
    loaded = store.read("x")
    assert loaded.stage == LifecycleStage.CHECKED
