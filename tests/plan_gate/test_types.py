from __future__ import annotations

from datetime import datetime, timezone

from organism.dod import Criterion, DoD
from organism.plan_gate import Plan, PlanStatus


def _sample_dod() -> DoD:
    return DoD(
        criteria=[
            Criterion(name="x", expected=1, weight=1.0, source="entity")
        ],
        confidence=0.7,
        _provenance={"entity": ["x"]},
    )


def _sample_plan() -> Plan:
    return Plan(
        id="abc-123",
        kind="create_entity",
        payload={"name": "alpha", "type": "demo"},
        dod=_sample_dod(),
        status=PlanStatus.PROPOSED,
        proposed_by="effector_x",
        proposed_at=datetime(2026, 5, 9, 12, 0, 0, tzinfo=timezone.utc),
    )


def test_plan_status_values():
    assert PlanStatus.PROPOSED.value == "proposed"
    assert PlanStatus.APPROVED.value == "approved"
    assert PlanStatus.REJECTED.value == "rejected"
    assert PlanStatus.APPLIED.value == "applied"
    assert PlanStatus.EXPIRED.value == "expired"


def test_plan_to_dict_basic():
    plan = _sample_plan()
    d = plan.to_dict()
    assert d["id"] == "abc-123"
    assert d["kind"] == "create_entity"
    assert d["status"] == "proposed"
    assert d["proposed_by"] == "effector_x"
    assert d["proposed_at"] == "2026-05-09T12:00:00+00:00"
    assert d["decided_at"] is None
    assert d["decided_by"] is None
    assert d["decision_reason"] == ""
    assert d["applied_at"] is None
    assert d["payload"] == {"name": "alpha", "type": "demo"}
    assert d["dod"]["criteria"][0]["name"] == "x"


def test_plan_round_trip_proposed():
    original = _sample_plan()
    restored = Plan.from_dict(original.to_dict())
    assert restored.id == original.id
    assert restored.kind == original.kind
    assert restored.payload == original.payload
    assert restored.status == original.status
    assert restored.proposed_by == original.proposed_by
    assert restored.proposed_at == original.proposed_at
    assert restored.decided_at is None
    assert restored.decision_reason == ""


def test_plan_round_trip_full_lifecycle():
    plan = Plan(
        id="full-1",
        kind="update_entity",
        payload={"k": "v"},
        dod=_sample_dod(),
        status=PlanStatus.APPLIED,
        proposed_by="ef_a",
        proposed_at=datetime(2026, 5, 9, 10, 0, 0, tzinfo=timezone.utc),
        decided_at=datetime(2026, 5, 9, 11, 0, 0, tzinfo=timezone.utc),
        decided_by="user_a",
        decision_reason="looks correct",
        applied_at=datetime(2026, 5, 9, 11, 5, 0, tzinfo=timezone.utc),
    )
    restored = Plan.from_dict(plan.to_dict())
    assert restored == plan


def test_plan_from_dict_accepts_datetime_objects():
    d = _sample_plan().to_dict()
    d["proposed_at"] = datetime(
        2026, 5, 9, 12, 0, 0, tzinfo=timezone.utc
    )
    plan = Plan.from_dict(d)
    assert plan.proposed_at == datetime(
        2026, 5, 9, 12, 0, 0, tzinfo=timezone.utc
    )


def test_plan_dod_round_trips_with_full_fields():
    plan = _sample_plan()
    d = plan.to_dict()
    restored = Plan.from_dict(d)
    assert restored.dod.criteria[0].name == "x"
    assert restored.dod.criteria[0].source == "entity"
    assert restored.dod.confidence == 0.7
    assert restored.dod._provenance == {"entity": ["x"]}
