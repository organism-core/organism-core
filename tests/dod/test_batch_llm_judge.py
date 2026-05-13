"""Tests for the validator's batched llm_judge path.

When a DoD contains two or more ``evaluator='llm_judge'`` criteria AND
the ``EvaluationContext`` provides a ``batch_llm_judge`` callable, the
validator collects those criteria and dispatches a single call instead
of N separate ones. Saves N-fold LLM cost and latency for DoDs with
multiple qualitative criteria.

Falls back to per-criterion ``llm_judge`` when:
- only one llm_judge criterion exists (no batching benefit)
- no ``batch_llm_judge`` callable is wired
- a criterion's key is missing in the result (clean per-criterion
  error reason)
"""

from __future__ import annotations

from typing import Any

import pytest

from organism.dod import (
    EVALUATOR_LLM_JUDGE,
    Criterion,
    DoD,
    DoDValidator,
    EvaluationContext,
)


# ---------- Batch fires when conditions met


def test_batched_when_two_llm_judge_criteria_and_callable_wired():
    call_log: list[list[str]] = []

    def batch_judge(criteria, result):
        call_log.append([c.name for c in criteria])
        return {c.name: (True, "batched ok") for c in criteria}

    dod = DoD(
        criteria=[
            Criterion(name="a", expected=True, evaluator=EVALUATOR_LLM_JUDGE),
            Criterion(name="b", expected=True, evaluator=EVALUATOR_LLM_JUDGE),
        ]
    )
    res = DoDValidator().validate(
        dod,
        {"a": "x", "b": "y"},
        context=EvaluationContext(batch_llm_judge=batch_judge),
    )
    # Exactly one batched call covering both criteria.
    assert len(call_log) == 1
    assert call_log[0] == ["a", "b"]
    assert res.all_satisfied is True
    assert all(r.reason == "batched ok" for r in res.criterion_results)


def test_batched_call_count_for_n_criteria_is_one():
    """The core performance promise: N llm_judge criteria => 1 call."""
    call_count = 0

    def batch_judge(criteria, result):
        nonlocal call_count
        call_count += 1
        return {c.name: (True, "ok") for c in criteria}

    dod = DoD(
        criteria=[
            Criterion(name=f"c{i}", expected=True, evaluator=EVALUATOR_LLM_JUDGE)
            for i in range(5)
        ]
    )
    DoDValidator().validate(
        dod,
        {f"c{i}": "v" for i in range(5)},
        context=EvaluationContext(batch_llm_judge=batch_judge),
    )
    assert call_count == 1


# ---------- Fallback paths


def test_no_batch_callable_falls_back_to_per_criterion():
    per_call_count = 0

    def per_judge(criterion, actual, result):
        nonlocal per_call_count
        per_call_count += 1
        return True, "per-criterion"

    dod = DoD(
        criteria=[
            Criterion(name="a", expected=True, evaluator=EVALUATOR_LLM_JUDGE),
            Criterion(name="b", expected=True, evaluator=EVALUATOR_LLM_JUDGE),
        ]
    )
    DoDValidator().validate(
        dod,
        {"a": "x", "b": "y"},
        context=EvaluationContext(llm_judge=per_judge),
    )
    # Per-criterion path: 2 calls.
    assert per_call_count == 2


def test_single_llm_judge_criterion_does_not_batch():
    """Batching only fires when there's actual benefit (>=2 criteria).
    A single criterion runs the per-criterion path even if batch_llm_judge
    is wired — keeps behavior identical between single-criterion DoDs
    with or without the batch callable."""
    batch_calls = 0
    per_calls = 0

    def batch_judge(criteria, result):
        nonlocal batch_calls
        batch_calls += 1
        return {c.name: (True, "ok") for c in criteria}

    def per_judge(criterion, actual, result):
        nonlocal per_calls
        per_calls += 1
        return True, "per"

    dod = DoD(
        criteria=[
            Criterion(name="solo", expected=True, evaluator=EVALUATOR_LLM_JUDGE),
        ]
    )
    DoDValidator().validate(
        dod,
        {"solo": "v"},
        context=EvaluationContext(
            llm_judge=per_judge, batch_llm_judge=batch_judge
        ),
    )
    assert batch_calls == 0
    assert per_calls == 1


def test_missing_key_falls_back_to_per_criterion_error_reason():
    """Criteria with keys missing in result skip the batch and get the
    clean per-criterion 'key not found' reason — better debuggability."""

    def batch_judge(criteria, result):
        return {c.name: (True, "should not be called for missing keys")
                for c in criteria}

    dod = DoD(
        criteria=[
            Criterion(name="present", expected=True, evaluator=EVALUATOR_LLM_JUDGE),
            Criterion(name="missing", expected=True, evaluator=EVALUATOR_LLM_JUDGE),
        ]
    )
    res = DoDValidator().validate(
        dod,
        {"present": "x"},  # 'missing' not in result
        context=EvaluationContext(batch_llm_judge=batch_judge),
    )
    present_result = next(r for r in res.criterion_results if r.name == "present")
    missing_result = next(r for r in res.criterion_results if r.name == "missing")
    # 'present' was batched (only 1 criterion in batch group → batch
    # does not fire for n=1 either, falls to per-criterion path with
    # no llm_judge callable, fails with "no llm_judge callable").
    # But since batch is wired and no llm_judge is wired, the single
    # leftover criterion goes through per-criterion with default
    # LlmJudgeEvaluator (no callable → fails).
    assert "not found" in missing_result.reason
    # The single 'present' criterion didn't batch (only 1 eligible),
    # fell through to per-criterion llm_judge with no callable.
    assert "no llm_judge callable" in present_result.reason


# ---------- Mixed-evaluator DoDs


def test_mixed_evaluators_only_llm_judge_criteria_are_batched():
    """A DoD with rule + llm_judge criteria: only the llm_judge ones
    get batched. Rule criteria use the per-criterion comparator."""
    batch_log: list[list[str]] = []

    def batch_judge(criteria, result):
        batch_log.append([c.name for c in criteria])
        return {c.name: (True, "batched") for c in criteria}

    dod = DoD(
        criteria=[
            Criterion(name="count", expected="1..5"),  # rule
            Criterion(name="quality_a", expected=True, evaluator=EVALUATOR_LLM_JUDGE),
            Criterion(name="quality_b", expected=True, evaluator=EVALUATOR_LLM_JUDGE),
            Criterion(name="approved", expected=True),  # rule
        ]
    )
    res = DoDValidator().validate(
        dod,
        {"count": 3, "quality_a": "x", "quality_b": "y", "approved": True},
        context=EvaluationContext(batch_llm_judge=batch_judge),
    )
    # Exactly one batch call, covering only the 2 llm_judge criteria.
    assert len(batch_log) == 1
    assert set(batch_log[0]) == {"quality_a", "quality_b"}
    # All 4 satisfied.
    assert res.all_satisfied is True


# ---------- Result-ordering preservation


def test_batch_preserves_output_ordering():
    """The output ``criterion_results`` order must match ``dod.criteria``
    order regardless of batching."""

    def batch_judge(criteria, result):
        return {c.name: (True, "ok") for c in criteria}

    dod = DoD(
        criteria=[
            Criterion(name="first", expected=True, evaluator=EVALUATOR_LLM_JUDGE),
            Criterion(name="second", expected=42),  # rule, not batched
            Criterion(name="third", expected=True, evaluator=EVALUATOR_LLM_JUDGE),
            Criterion(name="fourth", expected=True, evaluator=EVALUATOR_LLM_JUDGE),
        ]
    )
    res = DoDValidator().validate(
        dod,
        {"first": "v", "second": 42, "third": "v", "fourth": "v"},
        context=EvaluationContext(batch_llm_judge=batch_judge),
    )
    assert [r.name for r in res.criterion_results] == [
        "first",
        "second",
        "third",
        "fourth",
    ]


# ---------- Error paths


def test_batch_callable_raising_yields_clear_reason_for_all_in_batch():
    def boom(criteria, result):
        raise RuntimeError("kapow")

    dod = DoD(
        criteria=[
            Criterion(name="a", expected=True, evaluator=EVALUATOR_LLM_JUDGE),
            Criterion(name="b", expected=True, evaluator=EVALUATOR_LLM_JUDGE),
        ]
    )
    res = DoDValidator().validate(
        dod,
        {"a": "x", "b": "y"},
        context=EvaluationContext(batch_llm_judge=boom),
    )
    assert all(not r.satisfied for r in res.criterion_results)
    assert all("batch evaluator error" in r.reason for r in res.criterion_results)
    assert all("kapow" in r.reason for r in res.criterion_results)


def test_batch_callable_returning_non_dict_yields_clear_reason():
    def broken(criteria, result):
        return ["not", "a", "dict"]  # wrong shape

    dod = DoD(
        criteria=[
            Criterion(name="a", expected=True, evaluator=EVALUATOR_LLM_JUDGE),
            Criterion(name="b", expected=True, evaluator=EVALUATOR_LLM_JUDGE),
        ]
    )
    res = DoDValidator().validate(
        dod,
        {"a": "x", "b": "y"},
        context=EvaluationContext(batch_llm_judge=broken),
    )
    assert all("batch evaluator error" in r.reason for r in res.criterion_results)
    assert all("must return a dict" in r.reason for r in res.criterion_results)


def test_batch_missing_verdict_for_some_criterion_yields_clear_reason():
    """If the batch callable returns a dict but skips a criterion, that
    criterion fails with a specific 'no verdict' reason — distinct from
    a normal False verdict."""

    def partial(criteria, result):
        # Only return verdict for first criterion, skip the second.
        return {criteria[0].name: (True, "ok for first")}

    dod = DoD(
        criteria=[
            Criterion(name="a", expected=True, evaluator=EVALUATOR_LLM_JUDGE),
            Criterion(name="b", expected=True, evaluator=EVALUATOR_LLM_JUDGE),
        ]
    )
    res = DoDValidator().validate(
        dod,
        {"a": "x", "b": "y"},
        context=EvaluationContext(batch_llm_judge=partial),
    )
    by_name = {r.name: r for r in res.criterion_results}
    assert by_name["a"].satisfied is True
    assert by_name["b"].satisfied is False
    assert "did not return a verdict" in by_name["b"].reason


def test_batch_malformed_verdict_tuple_yields_clear_reason():
    """A verdict that isn't a (bool, str)-shaped tuple fails the
    criterion with a 'malformed verdict' reason — distinct from a
    normal False verdict."""

    def malformed(criteria, result):
        # First returns a single bool (not a tuple), second is fine.
        return {
            criteria[0].name: True,  # type: ignore[dict-item]
            criteria[1].name: (True, "ok"),
        }

    dod = DoD(
        criteria=[
            Criterion(name="a", expected=True, evaluator=EVALUATOR_LLM_JUDGE),
            Criterion(name="b", expected=True, evaluator=EVALUATOR_LLM_JUDGE),
        ]
    )
    res = DoDValidator().validate(
        dod,
        {"a": "x", "b": "y"},
        context=EvaluationContext(batch_llm_judge=malformed),
    )
    by_name = {r.name: r for r in res.criterion_results}
    assert by_name["b"].satisfied is True
    assert by_name["a"].satisfied is False
    assert "malformed verdict" in by_name["a"].reason


# ---------- Mixed satisfied/unsatisfied in batch


def test_batch_handles_mixed_satisfied_unsatisfied():
    def judge(criteria, result):
        return {
            "passing": (True, "good"),
            "failing": (False, "too short"),
        }

    dod = DoD(
        criteria=[
            Criterion(name="passing", expected=True, evaluator=EVALUATOR_LLM_JUDGE),
            Criterion(name="failing", expected=True, evaluator=EVALUATOR_LLM_JUDGE),
        ]
    )
    res = DoDValidator().validate(
        dod,
        {"passing": "v", "failing": "v"},
        context=EvaluationContext(batch_llm_judge=judge),
    )
    by_name = {r.name: r for r in res.criterion_results}
    assert by_name["passing"].satisfied is True
    assert by_name["passing"].reason == "good"
    assert by_name["failing"].satisfied is False
    assert by_name["failing"].reason == "too short"
