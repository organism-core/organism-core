from pathlib import Path
from typing import Any

import pytest

from organism.dod import (
    Criterion,
    CriterionResult,
    DoD,
    DoDEngine,
    DoDEngineSettings,
    DoDValidator,
    EntityFrontmatterSettings,
    EntityFrontmatterSource,
    ValidationResult,
)
from organism.dod.sources.entity_frontmatter import CONTEXT_KEY_ENTITY_ID
from organism.memory import Entity, EntityStore


# Empty / vacuous


def test_validate_empty_dod():
    res = DoDValidator().validate(DoD(), {})
    assert res.criterion_results == []
    assert res.score == 0.0
    assert res.all_satisfied is True


# Equality


def test_boolean_equality_satisfied():
    dod = DoD(criteria=[Criterion(name="approved", expected=True)])
    res = DoDValidator().validate(dod, {"approved": True})
    assert res.criterion_results[0].satisfied is True
    assert res.criterion_results[0].reason == ""


def test_boolean_equality_not_satisfied():
    dod = DoD(criteria=[Criterion(name="approved", expected=True)])
    res = DoDValidator().validate(dod, {"approved": False})
    assert res.criterion_results[0].satisfied is False
    assert "expected True" in res.criterion_results[0].reason


def test_string_equality():
    dod = DoD(criteria=[Criterion(name="status", expected="ok")])
    assert DoDValidator().validate(dod, {"status": "ok"}).all_satisfied
    assert not DoDValidator().validate(dod, {"status": "fail"}).all_satisfied


def test_int_equality():
    dod = DoD(criteria=[Criterion(name="x", expected=42)])
    assert DoDValidator().validate(dod, {"x": 42}).all_satisfied
    assert not DoDValidator().validate(dod, {"x": 43}).all_satisfied


def test_list_equality():
    dod = DoD(criteria=[Criterion(name="tags", expected=["a", "b"])])
    assert DoDValidator().validate(dod, {"tags": ["a", "b"]}).all_satisfied
    assert not DoDValidator().validate(
        dod, {"tags": ["a", "c"]}
    ).all_satisfied


# Callable


def test_callable_satisfied():
    crit = Criterion(name="x", expected=lambda v: v > 0)
    res = DoDValidator().validate(DoD(criteria=[crit]), {"x": 5})
    assert res.criterion_results[0].satisfied is True


def test_callable_not_satisfied():
    crit = Criterion(name="x", expected=lambda v: v > 0)
    res = DoDValidator().validate(DoD(criteria=[crit]), {"x": -1})
    assert res.criterion_results[0].satisfied is False
    assert "callable returned False" in res.criterion_results[0].reason


def test_callable_returning_falsy_treated_as_not_satisfied():
    crit = Criterion(name="x", expected=lambda v: None)
    res = DoDValidator().validate(DoD(criteria=[crit]), {"x": 5})
    assert res.criterion_results[0].satisfied is False


def test_callable_raising_exception_caught_with_reason():
    def bad(v: Any) -> bool:
        raise RuntimeError("boom")

    crit = Criterion(name="x", expected=bad)
    res = DoDValidator().validate(DoD(criteria=[crit]), {"x": 5})
    assert res.criterion_results[0].satisfied is False
    assert "comparator error" in res.criterion_results[0].reason
    assert "boom" in res.criterion_results[0].reason


# Range strings


def test_range_inside():
    dod = DoD(criteria=[Criterion(name="rooms", expected="25..35")])
    assert DoDValidator().validate(dod, {"rooms": 30}).all_satisfied


def test_range_below():
    dod = DoD(criteria=[Criterion(name="rooms", expected="25..35")])
    res = DoDValidator().validate(dod, {"rooms": 20})
    assert res.criterion_results[0].satisfied is False
    assert "not in [25.0, 35.0]" in res.criterion_results[0].reason


def test_range_above():
    dod = DoD(criteria=[Criterion(name="rooms", expected="25..35")])
    assert not DoDValidator().validate(dod, {"rooms": 40}).all_satisfied


def test_range_inclusive_endpoints():
    dod = DoD(criteria=[Criterion(name="rooms", expected="25..35")])
    assert DoDValidator().validate(dod, {"rooms": 25}).all_satisfied
    assert DoDValidator().validate(dod, {"rooms": 35}).all_satisfied


def test_range_with_floats():
    dod = DoD(criteria=[Criterion(name="ratio", expected="0.1..0.5")])
    assert DoDValidator().validate(dod, {"ratio": 0.25}).all_satisfied


def test_range_actual_string_numeric_coerced():
    dod = DoD(criteria=[Criterion(name="rooms", expected="25..35")])
    assert DoDValidator().validate(dod, {"rooms": "30"}).all_satisfied


def test_range_actual_non_numeric_fails():
    dod = DoD(criteria=[Criterion(name="rooms", expected="25..35")])
    res = DoDValidator().validate(dod, {"rooms": "lots"})
    assert res.criterion_results[0].satisfied is False
    assert "not numeric" in res.criterion_results[0].reason


def test_range_negative_numbers():
    dod = DoD(criteria=[Criterion(name="x", expected="-10..-5")])
    assert DoDValidator().validate(dod, {"x": -7}).all_satisfied
    assert not DoDValidator().validate(dod, {"x": 0}).all_satisfied


# Thresholds


def test_threshold_gte_satisfied():
    dod = DoD(criteria=[Criterion(name="conf", expected=">=0.9")])
    assert DoDValidator().validate(dod, {"conf": 0.95}).all_satisfied


def test_threshold_gte_at_boundary():
    dod = DoD(criteria=[Criterion(name="conf", expected=">=0.9")])
    assert DoDValidator().validate(dod, {"conf": 0.9}).all_satisfied


def test_threshold_gt_strict():
    dod = DoD(criteria=[Criterion(name="conf", expected=">0.9")])
    assert not DoDValidator().validate(dod, {"conf": 0.9}).all_satisfied


def test_threshold_lte():
    dod = DoD(criteria=[Criterion(name="errors", expected="<=3")])
    assert DoDValidator().validate(dod, {"errors": 3}).all_satisfied
    assert not DoDValidator().validate(dod, {"errors": 4}).all_satisfied


def test_threshold_lt():
    dod = DoD(criteria=[Criterion(name="errors", expected="<5")])
    assert DoDValidator().validate(dod, {"errors": 4}).all_satisfied
    assert not DoDValidator().validate(dod, {"errors": 5}).all_satisfied


def test_percent_threshold():
    dod = DoD(criteria=[Criterion(name="rwd", expected=">=90%")])
    assert DoDValidator().validate(dod, {"rwd": 95}).all_satisfied
    assert not DoDValidator().validate(dod, {"rwd": 85}).all_satisfied


def test_percent_actual_string_with_percent_suffix():
    dod = DoD(criteria=[Criterion(name="rwd", expected=">=90%")])
    assert DoDValidator().validate(dod, {"rwd": "95%"}).all_satisfied


def test_threshold_with_whitespace():
    dod = DoD(criteria=[Criterion(name="x", expected=">= 5")])
    assert DoDValidator().validate(dod, {"x": 5}).all_satisfied


def test_threshold_unparseable_value_raises_caught_as_unsatisfied():
    dod = DoD(criteria=[Criterion(name="x", expected=">=abc")])
    res = DoDValidator().validate(dod, {"x": 5})
    assert res.criterion_results[0].satisfied is False
    assert "comparator error" in res.criterion_results[0].reason


# Bool-as-int rejection


def test_bool_actual_rejected_for_numeric_range():
    dod = DoD(criteria=[Criterion(name="x", expected="1..5")])
    res = DoDValidator().validate(dod, {"x": True})
    assert res.criterion_results[0].satisfied is False
    assert "not numeric" in res.criterion_results[0].reason


def test_bool_actual_rejected_for_threshold():
    dod = DoD(criteria=[Criterion(name="x", expected=">=1")])
    res = DoDValidator().validate(dod, {"x": True})
    assert res.criterion_results[0].satisfied is False


# Missing keys


def test_missing_key_not_satisfied():
    dod = DoD(criteria=[Criterion(name="x", expected=42)])
    res = DoDValidator().validate(dod, {})
    assert res.criterion_results[0].satisfied is False
    assert res.criterion_results[0].actual is None
    assert "not found" in res.criterion_results[0].reason


def test_explicit_none_value_distinct_from_missing():
    dod = DoD(criteria=[Criterion(name="x", expected=None)])
    res = DoDValidator().validate(dod, {"x": None})
    assert res.criterion_results[0].satisfied is True
    assert res.criterion_results[0].actual is None
    assert res.criterion_results[0].reason == ""


# Score


def test_score_all_satisfied():
    dod = DoD(
        criteria=[
            Criterion(name="a", expected=1, weight=1.0),
            Criterion(name="b", expected=2, weight=2.0),
        ]
    )
    res = DoDValidator().validate(dod, {"a": 1, "b": 2})
    assert res.score == 1.0
    assert res.all_satisfied is True


def test_score_partial_weighted():
    dod = DoD(
        criteria=[
            Criterion(name="a", expected=1, weight=1.0),
            Criterion(name="b", expected=2, weight=3.0),
        ]
    )
    res = DoDValidator().validate(dod, {"a": 999, "b": 2})
    assert res.score == pytest.approx(0.75)
    assert res.all_satisfied is False


def test_score_none_satisfied():
    dod = DoD(
        criteria=[
            Criterion(name="a", expected=1, weight=1.0),
            Criterion(name="b", expected=2, weight=2.0),
        ]
    )
    res = DoDValidator().validate(dod, {})
    assert res.score == 0.0
    assert res.all_satisfied is False


def test_score_zero_total_weight_returns_zero():
    dod = DoD(criteria=[Criterion(name="a", expected=1, weight=0.0)])
    res = DoDValidator().validate(dod, {"a": 1})
    assert res.score == 0.0


# Result accessors


def test_unsatisfied_returns_only_failures():
    dod = DoD(
        criteria=[
            Criterion(name="a", expected=1),
            Criterion(name="b", expected=2),
            Criterion(name="c", expected=3),
        ]
    )
    res = DoDValidator().validate(dod, {"a": 1, "b": 999, "c": 3})
    assert [r.name for r in res.unsatisfied] == ["b"]


def test_unsatisfied_empty_when_all_pass():
    dod = DoD(criteria=[Criterion(name="a", expected=1)])
    res = DoDValidator().validate(dod, {"a": 1})
    assert res.unsatisfied == []


# Serialization


def test_validation_result_to_dict_round_trip():
    dod = DoD(
        criteria=[
            Criterion(name="a", expected=1, weight=2.0, source="entity")
        ]
    )
    res = DoDValidator().validate(dod, {"a": 1})
    d = res.to_dict()
    assert d["score"] == 1.0
    assert d["all_satisfied"] is True
    assert len(d["criterion_results"]) == 1
    cr = d["criterion_results"][0]
    assert cr == {
        "name": "a",
        "satisfied": True,
        "weight": 2.0,
        "expected": 1,
        "actual": 1,
        "reason": "",
        "evaluator": "rule",
    }


def test_criterion_result_dataclass_fields():
    cr = CriterionResult(
        name="x",
        satisfied=True,
        weight=1.5,
        expected=42,
        actual=42,
        reason="",
    )
    assert cr.to_dict()["weight"] == 1.5


def test_validation_result_default_empty():
    vr = ValidationResult()
    assert vr.criterion_results == []
    assert vr.score == 0.0
    assert vr.all_satisfied is True
    assert vr.unsatisfied == []


# DoD invariance


def test_validate_does_not_mutate_dod():
    dod = DoD(
        criteria=[Criterion(name="x", expected=1, weight=1.0)],
        clarification_needed=["q"],
        confidence=0.5,
    )
    DoDValidator().validate(dod, {"x": 1})
    assert dod.criteria[0].name == "x"
    assert dod.clarification_needed == ["q"]
    assert dod.confidence == 0.5


# Engine -> Validator integration


def test_full_flow_engine_to_validator(tmp_path: Path):
    store = EntityStore(tmp_path)
    store.write(
        "task_42",
        Entity(
            frontmatter={
                "dod": {
                    "criteria": [
                        {
                            "name": "rooms_count",
                            "expected": "25..35",
                            "weight": 1.0,
                        },
                        {
                            "name": "approved",
                            "expected": True,
                            "weight": 0.5,
                        },
                    ]
                }
            },
            body="",
        ),
    )

    engine = DoDEngine(
        sources=[
            EntityFrontmatterSource(
                store=store,
                settings=EntityFrontmatterSettings(confidence_when_loaded=0.9),
            )
        ],
        settings=DoDEngineSettings(threshold=0.5),
    )
    dod = engine.derive(
        request="any", context={CONTEXT_KEY_ENTITY_ID: "task_42"}
    )

    action_result = {"rooms_count": 30, "approved": False}
    validation = DoDValidator().validate(dod, action_result)

    assert validation.score == pytest.approx(1.0 / 1.5)
    assert validation.all_satisfied is False
    assert [r.name for r in validation.unsatisfied] == ["approved"]
    assert validation.criterion_results[0].satisfied is True
    assert validation.criterion_results[1].satisfied is False
