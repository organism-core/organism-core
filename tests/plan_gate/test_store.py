from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from organism.dod import DoD
from organism.plan_gate import PLAN_FILE_SUFFIX, Plan, PlanStatus, PlanStore


def _make_plan(
    plan_id: str = "abc-123",
    kind: str = "create_entity",
    status: PlanStatus = PlanStatus.PROPOSED,
) -> Plan:
    return Plan(
        id=plan_id,
        kind=kind,
        payload={"k": "v"},
        dod=DoD(),
        status=status,
        proposed_by="ef",
        proposed_at=datetime(2026, 5, 9, 12, 0, 0, tzinfo=timezone.utc),
    )


def test_write_creates_file_under_kind_dir(tmp_path: Path):
    store = PlanStore(tmp_path)
    plan = _make_plan(plan_id="p1", kind="create_entity")
    store.write(plan)
    expected = tmp_path / "create_entity" / f"p1{PLAN_FILE_SUFFIX}"
    assert expected.exists()


def test_read_round_trip(tmp_path: Path):
    store = PlanStore(tmp_path)
    plan = _make_plan(plan_id="p1")
    store.write(plan)
    loaded = store.read("p1")
    assert loaded == plan


def test_read_missing_raises(tmp_path: Path):
    store = PlanStore(tmp_path)
    with pytest.raises(FileNotFoundError, match="Plan 'ghost' not found"):
        store.read("ghost")


def test_read_walks_kind_dirs_when_kind_unknown(tmp_path: Path):
    store = PlanStore(tmp_path)
    store.write(_make_plan(plan_id="p1", kind="kind_a"))
    store.write(_make_plan(plan_id="p2", kind="kind_b"))
    assert store.read("p1").kind == "kind_a"
    assert store.read("p2").kind == "kind_b"


def test_exists(tmp_path: Path):
    store = PlanStore(tmp_path)
    assert not store.exists("p1")
    store.write(_make_plan(plan_id="p1"))
    assert store.exists("p1")
    assert not store.exists("ghost")


def test_list_empty_root(tmp_path: Path):
    assert PlanStore(tmp_path).list() == []


def test_list_missing_root(tmp_path: Path):
    assert PlanStore(tmp_path / "nonexistent").list() == []


def test_list_all_kinds(tmp_path: Path):
    store = PlanStore(tmp_path)
    store.write(_make_plan(plan_id="p1", kind="kind_a"))
    store.write(_make_plan(plan_id="p2", kind="kind_b"))
    plans = store.list()
    assert {p.id for p in plans} == {"p1", "p2"}


def test_list_filters_by_kind(tmp_path: Path):
    store = PlanStore(tmp_path)
    store.write(_make_plan(plan_id="p1", kind="kind_a"))
    store.write(_make_plan(plan_id="p2", kind="kind_b"))
    store.write(_make_plan(plan_id="p3", kind="kind_a"))
    plans = store.list(kind="kind_a")
    assert {p.id for p in plans} == {"p1", "p3"}


def test_list_filters_by_status(tmp_path: Path):
    store = PlanStore(tmp_path)
    store.write(_make_plan(plan_id="p1", status=PlanStatus.PROPOSED))
    store.write(_make_plan(plan_id="p2", status=PlanStatus.APPROVED))
    store.write(_make_plan(plan_id="p3", status=PlanStatus.PROPOSED))
    plans = store.list(status=PlanStatus.PROPOSED)
    assert {p.id for p in plans} == {"p1", "p3"}


def test_list_filters_by_kind_and_status(tmp_path: Path):
    store = PlanStore(tmp_path)
    store.write(
        _make_plan(plan_id="p1", kind="kind_a", status=PlanStatus.PROPOSED)
    )
    store.write(
        _make_plan(plan_id="p2", kind="kind_a", status=PlanStatus.APPROVED)
    )
    store.write(
        _make_plan(plan_id="p3", kind="kind_b", status=PlanStatus.PROPOSED)
    )
    plans = store.list(kind="kind_a", status=PlanStatus.PROPOSED)
    assert [p.id for p in plans] == ["p1"]


def test_list_unknown_kind_returns_empty(tmp_path: Path):
    store = PlanStore(tmp_path)
    store.write(_make_plan(plan_id="p1", kind="real_kind"))
    assert store.list(kind="ghost_kind") == []


def test_write_overwrites_existing(tmp_path: Path):
    store = PlanStore(tmp_path)
    store.write(_make_plan(plan_id="p1", status=PlanStatus.PROPOSED))
    store.write(_make_plan(plan_id="p1", status=PlanStatus.APPROVED))
    loaded = store.read("p1")
    assert loaded.status == PlanStatus.APPROVED
