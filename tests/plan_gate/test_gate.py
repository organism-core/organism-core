from __future__ import annotations

from pathlib import Path

import pytest

from organism.dod import Criterion, DoD
from organism.plan_gate import (
    PlanGate,
    PlanGateSettings,
    PlanStatus,
    PlanStore,
)


def _make_dod() -> DoD:
    return DoD(
        criteria=[Criterion(name="approved", expected=True, weight=1.0)],
        confidence=0.85,
    )


def _make_gate(tmp_path: Path, **settings_kwargs) -> PlanGate:
    store = PlanStore(tmp_path)
    settings = (
        PlanGateSettings(**settings_kwargs) if settings_kwargs else None
    )
    return PlanGate(store=store, settings=settings)


# propose


def test_propose_creates_plan_with_proposed_status(tmp_path: Path):
    gate = _make_gate(tmp_path)
    plan = gate.propose(
        kind="create_entity",
        payload={"k": "v"},
        dod=_make_dod(),
        proposed_by="ef_x",
    )
    assert plan.status == PlanStatus.PROPOSED
    assert plan.kind == "create_entity"
    assert plan.payload == {"k": "v"}
    assert plan.proposed_by == "ef_x"
    assert plan.proposed_at is not None
    assert plan.decided_at is None
    assert plan.applied_at is None


def test_propose_generates_unique_ids(tmp_path: Path):
    gate = _make_gate(tmp_path)
    p1 = gate.propose(
        kind="k", payload={}, dod=DoD(), proposed_by="ef"
    )
    p2 = gate.propose(
        kind="k", payload={}, dod=DoD(), proposed_by="ef"
    )
    assert p1.id != p2.id


def test_propose_persists_to_store(tmp_path: Path):
    gate = _make_gate(tmp_path)
    plan = gate.propose(
        kind="k", payload={}, dod=DoD(), proposed_by="ef"
    )
    loaded = gate.get(plan.id)
    assert loaded.id == plan.id
    assert loaded.status == PlanStatus.PROPOSED


def test_propose_copies_payload(tmp_path: Path):
    gate = _make_gate(tmp_path)
    payload = {"k": "v"}
    plan = gate.propose(
        kind="k", payload=payload, dod=DoD(), proposed_by="ef"
    )
    payload["mutated"] = True
    assert "mutated" not in plan.payload


# approve


def test_approve_transitions_proposed_to_approved(tmp_path: Path):
    gate = _make_gate(tmp_path)
    plan = gate.propose(
        kind="k", payload={}, dod=DoD(), proposed_by="ef"
    )
    approved = gate.approve(plan.id, decided_by="user_a", reason="ok")
    assert approved.status == PlanStatus.APPROVED
    assert approved.decided_by == "user_a"
    assert approved.decision_reason == "ok"
    assert approved.decided_at is not None
    assert approved.applied_at is None


def test_approve_persists_to_store(tmp_path: Path):
    gate = _make_gate(tmp_path)
    plan = gate.propose(
        kind="k", payload={}, dod=DoD(), proposed_by="ef"
    )
    gate.approve(plan.id, decided_by="user_a", reason="ok")
    loaded = gate.get(plan.id)
    assert loaded.status == PlanStatus.APPROVED


def test_approve_already_approved_raises(tmp_path: Path):
    gate = _make_gate(tmp_path)
    plan = gate.propose(
        kind="k", payload={}, dod=DoD(), proposed_by="ef"
    )
    gate.approve(plan.id, decided_by="user_a")
    with pytest.raises(ValueError, match="status is 'approved'"):
        gate.approve(plan.id, decided_by="user_b")


def test_approve_rejected_raises(tmp_path: Path):
    gate = _make_gate(tmp_path)
    plan = gate.propose(
        kind="k", payload={}, dod=DoD(), proposed_by="ef"
    )
    gate.reject(plan.id, decided_by="user_a")
    with pytest.raises(ValueError, match="status is 'rejected'"):
        gate.approve(plan.id, decided_by="user_b")


# reject


def test_reject_transitions_proposed_to_rejected(tmp_path: Path):
    gate = _make_gate(tmp_path)
    plan = gate.propose(
        kind="k", payload={}, dod=DoD(), proposed_by="ef"
    )
    rejected = gate.reject(
        plan.id, decided_by="user_a", reason="not safe"
    )
    assert rejected.status == PlanStatus.REJECTED
    assert rejected.decision_reason == "not safe"


def test_reject_already_decided_raises(tmp_path: Path):
    gate = _make_gate(tmp_path)
    plan = gate.propose(
        kind="k", payload={}, dod=DoD(), proposed_by="ef"
    )
    gate.approve(plan.id, decided_by="user_a")
    with pytest.raises(ValueError, match="status is 'approved'"):
        gate.reject(plan.id, decided_by="user_b")


# apply


def test_apply_transitions_approved_to_applied(tmp_path: Path):
    gate = _make_gate(tmp_path)
    plan = gate.propose(
        kind="k", payload={}, dod=DoD(), proposed_by="ef"
    )
    gate.approve(plan.id, decided_by="user_a")
    applied = gate.apply(plan.id)
    assert applied.status == PlanStatus.APPLIED
    assert applied.applied_at is not None


def test_apply_proposed_raises(tmp_path: Path):
    gate = _make_gate(tmp_path)
    plan = gate.propose(
        kind="k", payload={}, dod=DoD(), proposed_by="ef"
    )
    with pytest.raises(ValueError, match="status is 'proposed'"):
        gate.apply(plan.id)


def test_apply_rejected_raises(tmp_path: Path):
    gate = _make_gate(tmp_path)
    plan = gate.propose(
        kind="k", payload={}, dod=DoD(), proposed_by="ef"
    )
    gate.reject(plan.id, decided_by="user_a")
    with pytest.raises(ValueError, match="status is 'rejected'"):
        gate.apply(plan.id)


def test_apply_already_applied_raises(tmp_path: Path):
    gate = _make_gate(tmp_path)
    plan = gate.propose(
        kind="k", payload={}, dod=DoD(), proposed_by="ef"
    )
    gate.approve(plan.id, decided_by="user_a")
    gate.apply(plan.id)
    with pytest.raises(ValueError, match="status is 'applied'"):
        gate.apply(plan.id)


# missing plan


def test_approve_missing_plan_raises(tmp_path: Path):
    gate = _make_gate(tmp_path)
    with pytest.raises(FileNotFoundError):
        gate.approve("ghost", decided_by="user_a")


def test_get_missing_plan_raises(tmp_path: Path):
    gate = _make_gate(tmp_path)
    with pytest.raises(FileNotFoundError):
        gate.get("ghost")


# require_decision_reason


def test_approve_without_reason_when_required_raises(tmp_path: Path):
    gate = _make_gate(tmp_path, require_decision_reason=True)
    plan = gate.propose(
        kind="k", payload={}, dod=DoD(), proposed_by="ef"
    )
    with pytest.raises(ValueError, match="reason is required"):
        gate.approve(plan.id, decided_by="user_a")


def test_reject_without_reason_when_required_raises(tmp_path: Path):
    gate = _make_gate(tmp_path, require_decision_reason=True)
    plan = gate.propose(
        kind="k", payload={}, dod=DoD(), proposed_by="ef"
    )
    with pytest.raises(ValueError, match="reason is required"):
        gate.reject(plan.id, decided_by="user_a")


def test_approve_with_reason_when_required_succeeds(tmp_path: Path):
    gate = _make_gate(tmp_path, require_decision_reason=True)
    plan = gate.propose(
        kind="k", payload={}, dod=DoD(), proposed_by="ef"
    )
    approved = gate.approve(
        plan.id, decided_by="user_a", reason="approved-because-tests"
    )
    assert approved.status == PlanStatus.APPROVED


# DoD persistence


def test_dod_round_trips_through_propose_persist_get(tmp_path: Path):
    gate = _make_gate(tmp_path)
    dod = DoD(
        criteria=[
            Criterion(name="x", expected=1, weight=1.0, source="entity"),
            Criterion(name="y", expected="ok", weight=0.5, source="entity"),
        ],
        clarification_needed=[],
        confidence=0.9,
        evidence_sources=["self_check"],
        _provenance={"entity": ["x", "y"]},
    )
    plan = gate.propose(
        kind="k", payload={}, dod=dod, proposed_by="ef"
    )
    loaded = gate.get(plan.id)
    assert len(loaded.dod.criteria) == 2
    assert loaded.dod.criteria[0].name == "x"
    assert loaded.dod.criteria[1].weight == 0.5
    assert loaded.dod.confidence == 0.9
    assert loaded.dod._provenance == {"entity": ["x", "y"]}


# list


def test_list_returns_proposed_plans(tmp_path: Path):
    gate = _make_gate(tmp_path)
    p1 = gate.propose(
        kind="ka", payload={}, dod=DoD(), proposed_by="ef"
    )
    p2 = gate.propose(
        kind="kb", payload={}, dod=DoD(), proposed_by="ef"
    )
    proposed = gate.list(status=PlanStatus.PROPOSED)
    assert {p.id for p in proposed} == {p1.id, p2.id}


def test_list_after_approval_filters(tmp_path: Path):
    gate = _make_gate(tmp_path)
    p1 = gate.propose(
        kind="k", payload={}, dod=DoD(), proposed_by="ef"
    )
    p2 = gate.propose(
        kind="k", payload={}, dod=DoD(), proposed_by="ef"
    )
    gate.approve(p1.id, decided_by="user_a")
    proposed = gate.list(status=PlanStatus.PROPOSED)
    approved = gate.list(status=PlanStatus.APPROVED)
    assert [p.id for p in proposed] == [p2.id]
    assert [p.id for p in approved] == [p1.id]
