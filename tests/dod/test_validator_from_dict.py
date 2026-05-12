from __future__ import annotations

from organism.dod import CriterionResult, ValidationResult


def test_criterion_result_from_dict_minimal():
    cr = CriterionResult.from_dict(
        {
            "name": "x",
            "satisfied": True,
            "weight": 1.0,
            "expected": 1,
            "actual": 1,
        }
    )
    assert cr.name == "x"
    assert cr.satisfied is True
    assert cr.weight == 1.0
    assert cr.expected == 1
    assert cr.actual == 1
    assert cr.reason == ""


def test_criterion_result_round_trip():
    original = CriterionResult(
        name="x",
        satisfied=False,
        weight=0.5,
        expected="ok",
        actual="fail",
        reason="value mismatch",
    )
    restored = CriterionResult.from_dict(original.to_dict())
    assert restored == original


def test_criterion_result_from_dict_handles_none_expected_and_actual():
    cr = CriterionResult.from_dict(
        {
            "name": "x",
            "satisfied": True,
            "weight": 1.0,
            "expected": None,
            "actual": None,
        }
    )
    assert cr.expected is None
    assert cr.actual is None


def test_validation_result_from_dict_minimal():
    vr = ValidationResult.from_dict({})
    assert vr.criterion_results == []
    assert vr.score == 0.0


def test_validation_result_round_trip():
    original = ValidationResult(
        criterion_results=[
            CriterionResult(
                name="a",
                satisfied=True,
                weight=1.0,
                expected=1,
                actual=1,
            ),
            CriterionResult(
                name="b",
                satisfied=False,
                weight=2.0,
                expected="x",
                actual="y",
                reason="not equal",
            ),
        ],
        score=1.0 / 3.0,
    )
    restored = ValidationResult.from_dict(original.to_dict())
    assert restored == original


def test_validation_result_from_dict_ignores_all_satisfied_field():
    # to_dict includes all_satisfied; from_dict computes it via property,
    # so a stale value in input dict is ignored.
    data = {
        "criterion_results": [
            {
                "name": "x",
                "satisfied": True,
                "weight": 1.0,
                "expected": 1,
                "actual": 1,
            }
        ],
        "score": 1.0,
        "all_satisfied": False,
    }
    vr = ValidationResult.from_dict(data)
    assert vr.all_satisfied is True
