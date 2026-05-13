"""Evaluator strategies for DoD-criteria — one per `evaluator`-mode.

Each evaluator returns a `(satisfied, reason)` tuple. The Skelett ships with
three default modes:

    rule          deterministic comparator on the actual value (cheapest;
                  range / threshold / equality / callable, see _compare)
    self_check    effector self-attests in the result dict; validator
                  treats the value as the verdict (typically bool)
    llm_judge     external callable judges (effector + LLM); validator
                  delegates to ``EvaluationContext.llm_judge``

The Skelett does not depend on any LLM library — consumers inject their own
callable via ``EvaluationContext``. If no callable is provided when the mode
demands one, the criterion is treated as unsatisfied with a clear reason
(no silent pass).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from organism.dod.types import (
    EVALUATOR_LLM_JUDGE,
    EVALUATOR_RULE,
    EVALUATOR_SELF_CHECK,
    Criterion,
)

JudgeFn = Callable[[Criterion, Any, dict[str, Any]], tuple[bool, str]]
SelfCheckFn = Callable[[Criterion, Any, dict[str, Any]], tuple[bool, str]]
BatchJudgeFn = Callable[
    [list[Criterion], dict[str, Any]],
    dict[str, tuple[bool, str]],
]

_RANGE_RE = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*\.\.\s*(-?\d+(?:\.\d+)?)\s*$"
)
_CMP_RE = re.compile(r"^\s*(>=|<=|>|<)\s*(.+)$")
_OPS = {
    ">=": lambda a, b: a >= b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    "<": lambda a, b: a < b,
}


@dataclass
class EvaluationContext:
    """Optional callables and per-validation context.

    Per-criterion callables (``llm_judge`` and ``self_check``) are pure
    ``(criterion, actual, result_dict) -> (bool, reason)``. ``result_dict``
    is the full action result so a callable can inspect siblings.

    ``batch_llm_judge`` is the optional batched form: when wired AND a
    DoD contains two or more ``evaluator=llm_judge`` criteria, the
    validator collects them into one call instead of N separate calls.
    Signature: ``(criteria, result_dict) -> {criterion.name: (bool, reason)}``.
    Saves N-fold LLM cost and latency for DoDs with multiple qualitative
    criteria. Falls back to per-criterion ``llm_judge`` if not provided
    or if only one criterion exists.
    """

    llm_judge: JudgeFn | None = None
    self_check: SelfCheckFn | None = None
    batch_llm_judge: BatchJudgeFn | None = None


class Evaluator(Protocol):
    name: str

    def evaluate(
        self,
        criterion: Criterion,
        actual: Any,
        result: dict[str, Any],
        context: EvaluationContext,
    ) -> tuple[bool, str]: ...


class RuleEvaluator:
    name = EVALUATOR_RULE

    def evaluate(
        self,
        criterion: Criterion,
        actual: Any,
        result: dict[str, Any],
        context: EvaluationContext,
    ) -> tuple[bool, str]:
        return _compare(criterion.expected, actual)


class SelfCheckEvaluator:
    """Effector self-attests by writing a verdict into the result dict.

    By default, the actual is interpreted directly: ``expected == actual``
    (so a `True/True` self-check passes; `True/False` fails with a clear
    reason). If a `self_check` callable is provided in the context, it
    overrides this default — useful when the effector wants to keep raw
    output in the result and have a side-band callable derive the verdict.
    """

    name = EVALUATOR_SELF_CHECK

    def evaluate(
        self,
        criterion: Criterion,
        actual: Any,
        result: dict[str, Any],
        context: EvaluationContext,
    ) -> tuple[bool, str]:
        if context.self_check is not None:
            return context.self_check(criterion, actual, result)
        ok = criterion.expected == actual
        if ok:
            return True, ""
        return False, (
            f"self_check verdict {actual!r} != expected "
            f"{criterion.expected!r}"
        )


class LlmJudgeEvaluator:
    name = EVALUATOR_LLM_JUDGE

    def evaluate(
        self,
        criterion: Criterion,
        actual: Any,
        result: dict[str, Any],
        context: EvaluationContext,
    ) -> tuple[bool, str]:
        if context.llm_judge is None:
            return False, (
                "no llm_judge callable configured in EvaluationContext"
            )
        return context.llm_judge(criterion, actual, result)


def default_evaluators() -> dict[str, Evaluator]:
    return {
        EVALUATOR_RULE: RuleEvaluator(),
        EVALUATOR_SELF_CHECK: SelfCheckEvaluator(),
        EVALUATOR_LLM_JUDGE: LlmJudgeEvaluator(),
    }


def _compare(expected: Any, actual: Any) -> tuple[bool, str]:
    if callable(expected):
        try:
            ok = bool(expected(actual))
        except Exception as exc:
            return False, f"comparator error: {exc}"
        return ok, "" if ok else "callable returned False"

    if isinstance(expected, str):
        range_match = _RANGE_RE.match(expected)
        if range_match:
            low = float(range_match.group(1))
            high = float(range_match.group(2))
            actual_num = _coerce_number(actual)
            if actual_num is None:
                return False, f"actual {actual!r} not numeric for range"
            ok = low <= actual_num <= high
            return ok, "" if ok else f"{actual_num} not in [{low}, {high}]"

        cmp_match = _CMP_RE.match(expected)
        if cmp_match:
            op = cmp_match.group(1)
            threshold_str = cmp_match.group(2).rstrip().rstrip("%").rstrip()
            try:
                threshold = float(threshold_str)
            except ValueError as exc:
                return False, f"comparator error: {exc}"
            actual_num = _coerce_number(actual)
            if actual_num is None:
                return False, f"actual {actual!r} not numeric for {op}"
            ok = _OPS[op](actual_num, threshold)
            return ok, "" if ok else f"{actual_num} not {op} {threshold}"

    ok = expected == actual
    return ok, "" if ok else f"expected {expected!r}, got {actual!r}"


def _coerce_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.rstrip().rstrip("%").rstrip())
        except ValueError:
            return None
    return None
