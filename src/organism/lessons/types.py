from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from organism.dod.types import Criterion
from organism.provenance import Provenance


@dataclass
class Lesson:
    id: str
    kind: str
    observation: str
    provenance: Provenance
    recorded_at: datetime
    context_pattern: dict[str, Any] = field(default_factory=dict)
    criteria_hint: list[Criterion] = field(default_factory=list)
    confidence_delta: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "observation": self.observation,
            "provenance": self.provenance.to_dict(),
            "recorded_at": self.recorded_at.isoformat(),
            "context_pattern": dict(self.context_pattern),
            "criteria_hint": [c.to_dict() for c in self.criteria_hint],
            "confidence_delta": self.confidence_delta,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Lesson:
        return cls(
            id=data["id"],
            kind=data["kind"],
            observation=data["observation"],
            provenance=Provenance.from_dict(data["provenance"]),
            recorded_at=_parse_datetime(data["recorded_at"]),
            context_pattern=dict(data.get("context_pattern") or {}),
            criteria_hint=[
                Criterion.from_dict(c)
                for c in data.get("criteria_hint", [])
            ],
            confidence_delta=float(data.get("confidence_delta", 0.0)),
        )


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)
