from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from organism.dod.evaluators import (
    EvaluationContext,
    Evaluator,
    default_evaluators,
)
from organism.dod.types import Criterion, DoD


@dataclass
class CriterionResult:
    name: str
    satisfied: bool
    weight: float
    expected: Any
    actual: Any
    reason: str = ""
    evaluator: str = "rule"
    revision_strategy: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "name": self.name,
            "satisfied": self.satisfied,
            "weight": self.weight,
            "expected": self.expected,
            "actual": self.actual,
            "reason": self.reason,
            "evaluator": self.evaluator,
        }
        if self.revision_strategy is not None:
            d["revision_strategy"] = self.revision_strategy
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CriterionResult:
        return cls(
            name=data["name"],
            satisfied=bool(data["satisfied"]),
            weight=float(data["weight"]),
            expected=data.get("expected"),
            actual=data.get("actual"),
            reason=data.get("reason", ""),
            evaluator=data.get("evaluator", "rule"),
            revision_strategy=data.get("revision_strategy"),
        )


@dataclass
class ValidationResult:
    criterion_results: list[CriterionResult] = field(default_factory=list)
    score: float = 0.0

    @property
    def all_satisfied(self) -> bool:
        return all(r.satisfied for r in self.criterion_results)

    @property
    def unsatisfied(self) -> list[CriterionResult]:
        return [r for r in self.criterion_results if not r.satisfied]

    def is_fulfilled(self, threshold: float) -> bool:
        """Score-based fulfillment check.

        With threshold=1.0 this is equivalent to ``all_satisfied`` (the
        strict default). With a lower threshold (e.g. 0.8) the action is
        considered fulfilled even if some weak criteria fail, as long as
        the weighted score meets the bar.
        """
        if not self.criterion_results:
            return True
        return self.score >= threshold

    def to_dict(self) -> dict[str, Any]:
        return {
            "criterion_results": [r.to_dict() for r in self.criterion_results],
            "score": self.score,
            "all_satisfied": self.all_satisfied,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ValidationResult:
        return cls(
            criterion_results=[
                CriterionResult.from_dict(c)
                for c in data.get("criterion_results", [])
            ],
            score=float(data.get("score", 0.0)),
        )


class DoDValidator:
    """Checks an action result against DoD criteria.

    Dispatch is driven by ``Criterion.evaluator``:

        rule          deterministic comparator (range / threshold /
                      equality / callable). Cheapest mode.
        self_check    effector self-attests in the result dict
        llm_judge     external callable judges (consumer-injected)

    Comparator semantics for the ``rule`` evaluator on Criterion.expected:
        callable                 -> expected(actual) -> bool
        "lo..hi" string          -> numeric range, inclusive on both ends
        ">=N"/"<=N"/">N"/"<N"    -> threshold (optional '%' suffix)
        anything else            -> equality (==)
    """

    def __init__(
        self, evaluators: dict[str, Evaluator] | None = None
    ) -> None:
        self.evaluators = evaluators or default_evaluators()

    def validate(
        self,
        dod: DoD,
        result: dict[str, Any],
        *,
        context: EvaluationContext | None = None,
    ) -> ValidationResult:
        ctx = context or EvaluationContext()
        criterion_results = [
            self._check_criterion(c, result, ctx) for c in dod.criteria
        ]
        return ValidationResult(
            criterion_results=criterion_results,
            score=_weighted_score(criterion_results),
        )

    def _check_criterion(
        self,
        criterion: Criterion,
        result: dict[str, Any],
        context: EvaluationContext,
    ) -> CriterionResult:
        if criterion.name not in result:
            return CriterionResult(
                name=criterion.name,
                satisfied=False,
                weight=criterion.weight,
                expected=criterion.expected,
                actual=None,
                reason=f"key '{criterion.name}' not found in result",
                evaluator=criterion.evaluator,
                revision_strategy=criterion.revision_strategy,
            )

        actual = result[criterion.name]
        evaluator = self.evaluators.get(criterion.evaluator)
        if evaluator is None:
            return CriterionResult(
                name=criterion.name,
                satisfied=False,
                weight=criterion.weight,
                expected=criterion.expected,
                actual=actual,
                reason=(
                    f"no evaluator registered for "
                    f"{criterion.evaluator!r}"
                ),
                evaluator=criterion.evaluator,
                revision_strategy=criterion.revision_strategy,
            )

        try:
            satisfied, reason = evaluator.evaluate(
                criterion, actual, result, context
            )
        except Exception as exc:
            return CriterionResult(
                name=criterion.name,
                satisfied=False,
                weight=criterion.weight,
                expected=criterion.expected,
                actual=actual,
                reason=f"evaluator error: {exc}",
                evaluator=criterion.evaluator,
                revision_strategy=criterion.revision_strategy,
            )

        return CriterionResult(
            name=criterion.name,
            satisfied=satisfied,
            weight=criterion.weight,
            expected=criterion.expected,
            actual=actual,
            reason=reason,
            evaluator=criterion.evaluator,
            revision_strategy=criterion.revision_strategy,
        )


def _weighted_score(results: list[CriterionResult]) -> float:
    if not results:
        return 0.0
    total = sum(r.weight for r in results)
    if total == 0:
        return 0.0
    satisfied = sum(r.weight for r in results if r.satisfied)
    return satisfied / total
