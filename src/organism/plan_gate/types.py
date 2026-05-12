from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from organism.dod.types import DoD


class PlanStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"
    EXPIRED = "expired"


@dataclass
class Plan:
    id: str
    kind: str
    payload: dict[str, Any]
    dod: DoD
    status: PlanStatus
    proposed_by: str
    proposed_at: datetime
    decided_at: datetime | None = None
    decided_by: str | None = None
    decision_reason: str = ""
    applied_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "status": self.status.value,
            "proposed_by": self.proposed_by,
            "proposed_at": self.proposed_at.isoformat(),
            "decided_at": (
                self.decided_at.isoformat() if self.decided_at else None
            ),
            "decided_by": self.decided_by,
            "decision_reason": self.decision_reason,
            "applied_at": (
                self.applied_at.isoformat() if self.applied_at else None
            ),
            "payload": dict(self.payload),
            "dod": self.dod.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Plan:
        return cls(
            id=data["id"],
            kind=data["kind"],
            payload=dict(data.get("payload") or {}),
            dod=DoD.from_dict(data.get("dod") or {}),
            status=PlanStatus(data["status"]),
            proposed_by=data["proposed_by"],
            proposed_at=_parse_datetime(data["proposed_at"]),
            decided_at=_parse_datetime(data.get("decided_at")),
            decided_by=data.get("decided_by"),
            decision_reason=data.get("decision_reason", ""),
            applied_at=_parse_datetime(data.get("applied_at")),
        )


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)
