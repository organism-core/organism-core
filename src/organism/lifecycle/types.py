from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class LifecycleStage(str, Enum):
    MANUAL = "manual"
    PROPOSED = "proposed"
    CHECKED = "checked"
    ROUTINE = "routine"
    AUTONOMOUS = "autonomous"


STAGE_ORDER: tuple[LifecycleStage, ...] = (
    LifecycleStage.MANUAL,
    LifecycleStage.PROPOSED,
    LifecycleStage.CHECKED,
    LifecycleStage.ROUTINE,
    LifecycleStage.AUTONOMOUS,
)


def stage_above(stage: LifecycleStage) -> LifecycleStage | None:
    idx = STAGE_ORDER.index(stage)
    if idx + 1 < len(STAGE_ORDER):
        return STAGE_ORDER[idx + 1]
    return None


def stage_below(stage: LifecycleStage) -> LifecycleStage | None:
    idx = STAGE_ORDER.index(stage)
    if idx - 1 >= 0:
        return STAGE_ORDER[idx - 1]
    return None


@dataclass
class ActionOutcome:
    plan_id: str | None
    score: float
    recorded_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "score": self.score,
            "recorded_at": self.recorded_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActionOutcome:
        return cls(
            plan_id=data.get("plan_id"),
            score=float(data["score"]),
            recorded_at=_parse_datetime(data["recorded_at"]),
        )


@dataclass
class LifecycleTransition:
    from_stage: LifecycleStage
    to_stage: LifecycleStage
    reason: str
    transitioned_at: datetime

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_stage": self.from_stage.value,
            "to_stage": self.to_stage.value,
            "reason": self.reason,
            "transitioned_at": self.transitioned_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LifecycleTransition:
        return cls(
            from_stage=LifecycleStage(data["from_stage"]),
            to_stage=LifecycleStage(data["to_stage"]),
            reason=data["reason"],
            transitioned_at=_parse_datetime(data["transitioned_at"]),
        )


@dataclass
class LifecycleState:
    kind: str
    stage: LifecycleStage
    recent_outcomes: list[ActionOutcome] = field(default_factory=list)
    last_transition_at: datetime | None = None
    transition_history: list[LifecycleTransition] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "stage": self.stage.value,
            "recent_outcomes": [o.to_dict() for o in self.recent_outcomes],
            "last_transition_at": (
                self.last_transition_at.isoformat()
                if self.last_transition_at
                else None
            ),
            "transition_history": [
                t.to_dict() for t in self.transition_history
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LifecycleState:
        return cls(
            kind=data["kind"],
            stage=LifecycleStage(data["stage"]),
            recent_outcomes=[
                ActionOutcome.from_dict(o)
                for o in data.get("recent_outcomes", [])
            ],
            last_transition_at=_parse_datetime(
                data.get("last_transition_at")
            ),
            transition_history=[
                LifecycleTransition.from_dict(t)
                for t in data.get("transition_history", [])
            ],
        )


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)
