from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from organism.dod.types import DoD
from organism.dod.validator import ValidationResult
from organism.lifecycle.types import LifecycleTransition
from organism.plan_gate.types import Plan


class ActionStatus(str, Enum):
    MANUAL = "manual"
    PROPOSED = "proposed"
    APPLIED = "applied"
    DENIED = "denied"
    NEEDS_CLARIFICATION = "needs_clarification"


REVISION_OUTCOME_NONE = ""
REVISION_OUTCOME_COMPLETED = "completed"
REVISION_OUTCOME_EXHAUSTED = "exhausted"
REVISION_OUTCOME_ESCALATED = "escalated"
REVISION_OUTCOME_ROLLED_BACK = "rolled_back"
# Reserved for DoDs that are themselves incoherent with the request —
# e.g. clarification requirements that re-emerge during the revision
# loop, or contradictory criteria. Distinct from `exhausted` (out of
# attempts on an otherwise coherent rubric). Mirrors the distinction
# Anthropic's Outcomes feature makes between `max_iterations_reached`
# and `failed`.
REVISION_OUTCOME_FAILED = "failed"


@dataclass
class ActionResult:
    status: ActionStatus
    dod: DoD | None = None
    plan: Plan | None = None
    result: Any = None
    validation: ValidationResult | None = None
    transition: LifecycleTransition | None = None
    revision_pending: bool = False
    revision_attempts: int = 0
    revision_outcome: str = REVISION_OUTCOME_NONE
    warnings: list[str] = field(default_factory=list)
    reason: str = ""
