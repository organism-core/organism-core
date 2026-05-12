from __future__ import annotations

from typing import Any

import pytest

from organism.dod import (
    EVALUATOR_LLM_JUDGE,
    EVALUATOR_RULE,
    EVALUATOR_SELF_CHECK,
    Criterion,
    DoD,
    DoDValidator,
    EvaluationContext,
    LlmJudgeEvaluator,
    RuleEvaluator,
    SelfCheckEvaluator,
    default_evaluators,
)


# Criterion: evaluator field validation


def test_criterion_default_evaluator_is_rule():
    c = Criterion(name="x", expected=1)
    assert c.evaluator == EVALUATOR_RULE


def test_criterion_accepts_known_evaluators():
    for ev in (
        EVALUATOR_RULE,
        EVALUATOR_SELF_CHECK,
        EVALUATOR_LLM_JUDGE,
    ):
        Criterion(name="x", expected=1, evaluator=ev)


def test_criterion_rejects_unknown_evaluator():
    with pytest.raises(ValueError, match="unknown evaluator"):
        Criterion(name="x", expected=1, evaluator="bogus")


def test_criterion_to_dict_omits_default_evaluator():
    d = Criterion(name="x", expected=1).to_dict()
    assert "evaluator" not in d


def test_criterion_to_dict_includes_non_default_evaluator():
    d = Criterion(
        name="x", expected=True, evaluator=EVALUATOR_SELF_CHECK
    ).to_dict()
    assert d["evaluator"] == EVALUATOR_SELF_CHECK


def test_criterion_round_trip_preserves_evaluator():
    original = Criterion(
        name="x",
        expected=True,
        weight=0.5,
        evaluator=EVALUATOR_LLM_JUDGE,
    )
    restored = Criterion.from_dict(original.to_dict())
    assert restored == original


# RuleEvaluator — sanity, full coverage already in test_validator.py


def test_rule_evaluator_passes_simple_equality():
    ev = RuleEvaluator()
    c = Criterion(name="x", expected=42)
    ok, reason = ev.evaluate(c, 42, {"x": 42}, EvaluationContext())
    assert ok is True
    assert reason == ""


def test_rule_evaluator_fails_with_reason():
    ev = RuleEvaluator()
    c = Criterion(name="x", expected=42)
    ok, reason = ev.evaluate(c, 99, {"x": 99}, EvaluationContext())
    assert ok is False
    assert "expected 42" in reason


# SelfCheckEvaluator


def test_self_check_default_uses_equality_on_actual():
    ev = SelfCheckEvaluator()
    c = Criterion(
        name="topology_consistent",
        expected=True,
        evaluator=EVALUATOR_SELF_CHECK,
    )
    ok, _ = ev.evaluate(c, True, {"topology_consistent": True},
                        EvaluationContext())
    assert ok is True


def test_self_check_default_fails_when_verdict_mismatches():
    ev = SelfCheckEvaluator()
    c = Criterion(
        name="topology_consistent",
        expected=True,
        evaluator=EVALUATOR_SELF_CHECK,
    )
    ok, reason = ev.evaluate(c, False, {"topology_consistent": False},
                             EvaluationContext())
    assert ok is False
    assert "self_check verdict" in reason


def test_self_check_callable_overrides_default():
    captured: list[Any] = []

    def derive(criterion, actual, result):
        captured.append((criterion.name, actual, result))
        return True, "derived from callable"

    ev = SelfCheckEvaluator()
    c = Criterion(name="x", expected=True, evaluator=EVALUATOR_SELF_CHECK)
    ok, reason = ev.evaluate(
        c, "raw_output", {"x": "raw_output"},
        EvaluationContext(self_check=derive),
    )
    assert ok is True
    assert reason == "derived from callable"
    assert captured == [("x", "raw_output", {"x": "raw_output"})]


# LlmJudgeEvaluator


def test_llm_judge_unsatisfied_when_no_callable_configured():
    ev = LlmJudgeEvaluator()
    c = Criterion(name="x", expected="quality match",
                  evaluator=EVALUATOR_LLM_JUDGE)
    ok, reason = ev.evaluate(
        c, "some_output", {"x": "some_output"}, EvaluationContext()
    )
    assert ok is False
    assert "no llm_judge callable configured" in reason


def test_llm_judge_delegates_to_callable():
    def judge(criterion, actual, result):
        assert criterion.name == "tone"
        assert actual == "formal text"
        assert result == {"tone": "formal text"}
        return True, "tone matches"

    ev = LlmJudgeEvaluator()
    c = Criterion(
        name="tone", expected="formal", evaluator=EVALUATOR_LLM_JUDGE
    )
    ok, reason = ev.evaluate(
        c, "formal text", {"tone": "formal text"},
        EvaluationContext(llm_judge=judge),
    )
    assert ok is True
    assert reason == "tone matches"


# Validator dispatch


def test_validator_dispatches_to_rule_evaluator_by_default():
    dod = DoD(criteria=[Criterion(name="x", expected="1..5")])
    res = DoDValidator().validate(dod, {"x": 3})
    assert res.criterion_results[0].satisfied is True
    assert res.criterion_results[0].evaluator == "rule"


def test_validator_dispatches_to_self_check_evaluator():
    dod = DoD(
        criteria=[
            Criterion(
                name="schema_consistent",
                expected=True,
                evaluator=EVALUATOR_SELF_CHECK,
            )
        ]
    )
    res = DoDValidator().validate(dod, {"schema_consistent": True})
    assert res.criterion_results[0].satisfied is True
    assert res.criterion_results[0].evaluator == EVALUATOR_SELF_CHECK


def test_validator_dispatches_to_llm_judge_with_context():
    def judge(criterion, actual, result):
        return actual.startswith("formal"), "tone judged"

    dod = DoD(
        criteria=[
            Criterion(
                name="tone",
                expected="formal",
                evaluator=EVALUATOR_LLM_JUDGE,
            )
        ]
    )
    res = DoDValidator().validate(
        dod,
        {"tone": "formal restrained text"},
        context=EvaluationContext(llm_judge=judge),
    )
    assert res.criterion_results[0].satisfied is True
    assert res.criterion_results[0].evaluator == EVALUATOR_LLM_JUDGE


def test_validator_handles_evaluator_exception_with_reason():
    def boom(criterion, actual, result):
        raise RuntimeError("judge crashed")

    dod = DoD(
        criteria=[
            Criterion(
                name="x", expected=True, evaluator=EVALUATOR_LLM_JUDGE
            )
        ]
    )
    res = DoDValidator().validate(
        dod, {"x": "anything"},
        context=EvaluationContext(llm_judge=boom),
    )
    assert res.criterion_results[0].satisfied is False
    assert "evaluator error" in res.criterion_results[0].reason
    assert "judge crashed" in res.criterion_results[0].reason


def test_validator_unknown_evaluator_yields_clear_reason():
    # Bypass Criterion.__post_init__ validation by mutating after creation.
    c = Criterion(name="x", expected=1)
    object.__setattr__(c, "evaluator", "ghost_mode")

    res = DoDValidator().validate(DoD(criteria=[c]), {"x": 1})
    assert res.criterion_results[0].satisfied is False
    assert "no evaluator registered" in res.criterion_results[0].reason
    assert "ghost_mode" in res.criterion_results[0].reason


def test_validator_supports_custom_evaluator_registry():
    class AlwaysPass:
        name = "rule"

        def evaluate(self, criterion, actual, result, context):
            return True, "stub-pass"

    res = DoDValidator(evaluators={"rule": AlwaysPass()}).validate(
        DoD(criteria=[Criterion(name="x", expected=99)]), {"x": 1}
    )
    assert res.criterion_results[0].satisfied is True
    assert res.criterion_results[0].reason == "stub-pass"


def test_default_evaluators_returns_three_modes():
    evs = default_evaluators()
    assert set(evs.keys()) == {
        EVALUATOR_RULE,
        EVALUATOR_SELF_CHECK,
        EVALUATOR_LLM_JUDGE,
    }


# Mixed-evaluator DoD


def test_mixed_evaluators_in_one_dod():
    def judge(criterion, actual, result):
        return "ok" in actual, ""

    dod = DoD(
        criteria=[
            Criterion(name="count", expected="1..5"),
            Criterion(
                name="schema_ok",
                expected=True,
                evaluator=EVALUATOR_SELF_CHECK,
            ),
            Criterion(
                name="tone",
                expected="ok",
                evaluator=EVALUATOR_LLM_JUDGE,
                weight=0.5,
            ),
        ]
    )
    res = DoDValidator().validate(
        dod,
        {"count": 3, "schema_ok": True, "tone": "this looks ok"},
        context=EvaluationContext(llm_judge=judge),
    )
    assert res.all_satisfied is True
    assert [r.evaluator for r in res.criterion_results] == [
        EVALUATOR_RULE,
        EVALUATOR_SELF_CHECK,
        EVALUATOR_LLM_JUDGE,
    ]


def test_mixed_evaluator_partial_failure_propagates_to_score():
    def judge(criterion, actual, result):
        return False, "tone too informal"

    dod = DoD(
        criteria=[
            Criterion(name="count", expected="1..5", weight=1.0),
            Criterion(
                name="tone",
                expected="formal",
                evaluator=EVALUATOR_LLM_JUDGE,
                weight=1.0,
            ),
        ]
    )
    res = DoDValidator().validate(
        dod,
        {"count": 3, "tone": "yo"},
        context=EvaluationContext(llm_judge=judge),
    )
    assert res.score == pytest.approx(0.5)
    assert [r.name for r in res.unsatisfied] == ["tone"]
