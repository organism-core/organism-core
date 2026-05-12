from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


EVALUATOR_RULE = "rule"
EVALUATOR_SELF_CHECK = "self_check"
EVALUATOR_LLM_JUDGE = "llm_judge"

EVALUATORS = frozenset(
    {EVALUATOR_RULE, EVALUATOR_SELF_CHECK, EVALUATOR_LLM_JUDGE}
)

REVISION_RETRY_ALT_PARAMS = "retry_alt_params"
REVISION_ESCALATE_TO_HUMAN = "escalate_to_human"
REVISION_ROLLBACK_AND_LOG = "rollback_and_log"

REVISION_STRATEGIES = frozenset(
    {
        REVISION_RETRY_ALT_PARAMS,
        REVISION_ESCALATE_TO_HUMAN,
        REVISION_ROLLBACK_AND_LOG,
    }
)

# Severity ordering: strongest first. When unsatisfied criteria carry
# different revision strategies, the orchestrator picks the strongest
# one demanded by any of them (rollback > escalate > retry).
REVISION_STRATEGY_PRIORITY: tuple[str, ...] = (
    REVISION_ROLLBACK_AND_LOG,
    REVISION_ESCALATE_TO_HUMAN,
    REVISION_RETRY_ALT_PARAMS,
)


@dataclass
class Criterion:
    name: str
    expected: Any
    weight: float = 1.0
    source: str = ""
    evaluator: str = EVALUATOR_RULE
    revision_strategy: str | None = None

    def __post_init__(self) -> None:
        if self.evaluator not in EVALUATORS:
            raise ValueError(
                f"unknown evaluator {self.evaluator!r}; "
                f"expected one of {sorted(EVALUATORS)}"
            )
        if (
            self.revision_strategy is not None
            and self.revision_strategy not in REVISION_STRATEGIES
        ):
            raise ValueError(
                f"unknown revision_strategy {self.revision_strategy!r}; "
                f"expected one of {sorted(REVISION_STRATEGIES)} or None"
            )

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "name": self.name,
            "expected": self.expected,
            "weight": self.weight,
        }
        if self.source:
            d["source"] = self.source
        if self.evaluator != EVALUATOR_RULE:
            d["evaluator"] = self.evaluator
        if self.revision_strategy is not None:
            d["revision_strategy"] = self.revision_strategy
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Criterion:
        return cls(
            name=data["name"],
            expected=data["expected"],
            weight=float(data.get("weight", 1.0)),
            source=data.get("source", ""),
            evaluator=data.get("evaluator", EVALUATOR_RULE),
            revision_strategy=data.get("revision_strategy"),
        )


@dataclass
class SourceContribution:
    source_name: str
    criteria: list[Criterion] = field(default_factory=list)
    confidence_delta: float = 0.0
    clarifications: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass
class DoD:
    criteria: list[Criterion] = field(default_factory=list)
    clarification_needed: list[str] = field(default_factory=list)
    confidence: float = 0.0
    evidence_sources: list[str] = field(default_factory=list)
    _provenance: dict[str, list[str]] = field(default_factory=dict)

    def is_satisfied_for_act(self) -> bool:
        return not self.clarification_needed

    def to_dict(self) -> dict[str, Any]:
        return {
            "criteria": [c.to_dict() for c in self.criteria],
            "clarification_needed": list(self.clarification_needed),
            "confidence": self.confidence,
            "evidence_sources": list(self.evidence_sources),
            "_provenance": {k: list(v) for k, v in self._provenance.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DoD:
        return cls(
            criteria=[
                Criterion.from_dict(c) for c in data.get("criteria", [])
            ],
            clarification_needed=list(data.get("clarification_needed", [])),
            confidence=float(data.get("confidence", 0.0)),
            evidence_sources=list(data.get("evidence_sources", [])),
            _provenance={
                k: list(v) for k, v in data.get("_provenance", {}).items()
            },
        )
