from __future__ import annotations

from datetime import datetime, timezone

from organism.dod import (
    Criterion,
    CriterionResult,
    DoD,
    ValidationResult,
)
from organism.lifecycle import LifecycleStage
from organism.observability import Trace, truncate_repr
from organism.orchestrator import ActionStatus
from organism.provenance import Provenance


def _make_trace(
    status: ActionStatus = ActionStatus.APPLIED,
    stage: LifecycleStage = LifecycleStage.CHECKED,
) -> Trace:
    return Trace(
        id="trace-001",
        kind="create_entity",
        request_summary="'hello'",
        context={"entity_id": "alpha", "preloaded": True},
        stage=stage,
        status=status,
        dod=DoD(
            criteria=[Criterion(name="x", expected=1, source="test_source")],
            confidence=0.9,
        ),
        started_at=datetime(2026, 5, 9, 10, 0, 0, tzinfo=timezone.utc),
        completed_at=datetime(2026, 5, 9, 10, 0, 1, tzinfo=timezone.utc),
        provenance=Provenance(
            author="ef",
            timestamp=datetime(2026, 5, 9, 10, 0, 1, tzinfo=timezone.utc),
            source="orchestrator.execute",
        ),
    )


def test_to_dict_basic():
    trace = _make_trace()
    d = trace.to_dict()
    assert d["id"] == "trace-001"
    assert d["kind"] == "create_entity"
    assert d["status"] == "applied"
    assert d["stage"] == "checked"
    assert d["started_at"] == "2026-05-09T10:00:00+00:00"
    assert d["dod"]["criteria"][0]["name"] == "x"


def test_round_trip_minimal():
    trace = _make_trace()
    restored = Trace.from_dict(trace.to_dict())
    assert restored == trace


def test_round_trip_with_validation_and_transition():
    trace = _make_trace()
    trace.validation = ValidationResult(
        criterion_results=[
            CriterionResult(
                name="x",
                satisfied=True,
                weight=1.0,
                expected=1,
                actual=1,
            )
        ],
        score=1.0,
    )
    trace.transition_to = LifecycleStage.ROUTINE
    trace.plan_id = "plan-xyz"
    trace.result_summary = "{'ok': True}"
    trace.reason = "all good"
    restored = Trace.from_dict(trace.to_dict())
    assert restored == trace


def test_round_trip_proposed_with_plan_id():
    trace = _make_trace(status=ActionStatus.PROPOSED, stage=LifecycleStage.PROPOSED)
    trace.plan_id = "plan-abc"
    restored = Trace.from_dict(trace.to_dict())
    assert restored == trace


def test_to_dict_safes_non_yaml_context_values():
    class _Custom:
        def __repr__(self):
            return "_Custom()"

    trace = _make_trace()
    trace.context = {"obj": _Custom(), "num": 42, "str": "ok"}
    d = trace.to_dict()
    assert d["context"]["obj"] == "_Custom()"
    assert d["context"]["num"] == 42
    assert d["context"]["str"] == "ok"


def test_to_dict_handles_nested_context():
    trace = _make_trace()
    trace.context = {
        "outer": {"inner": [1, 2, 3]},
        "items": (4, 5, 6),
    }
    d = trace.to_dict()
    assert d["context"]["outer"] == {"inner": [1, 2, 3]}
    assert d["context"]["items"] == [4, 5, 6]


def test_truncate_repr_short_value_unchanged():
    assert truncate_repr("hi", max_length=100) == "'hi'"


def test_truncate_repr_long_value_cut_with_ellipsis():
    s = truncate_repr("x" * 100, max_length=20)
    assert len(s) == 20
    assert s.endswith("...")


def test_truncate_repr_zero_max_length_returns_empty():
    assert truncate_repr("anything", max_length=0) == ""


def test_truncate_repr_dict_value():
    s = truncate_repr({"k": 1}, max_length=100)
    assert s == "{'k': 1}"
