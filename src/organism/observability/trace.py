from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from organism.dod.types import DoD
from organism.dod.validator import ValidationResult
from organism.lifecycle.types import LifecycleStage
from organism.orchestrator.types import ActionStatus
from organism.provenance import Provenance


@dataclass
class Trace:
    id: str
    kind: str
    request_summary: str
    context: dict[str, Any]
    stage: LifecycleStage
    status: ActionStatus
    dod: DoD
    started_at: datetime
    completed_at: datetime
    provenance: Provenance

    plan_id: str | None = None
    result_summary: str | None = None
    validation: ValidationResult | None = None
    transition_to: LifecycleStage | None = None
    revision_pending: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "request_summary": self.request_summary,
            "context": _to_yaml_safe(self.context),
            "stage": self.stage.value,
            "status": self.status.value,
            "dod": self.dod.to_dict(),
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "provenance": self.provenance.to_dict(),
            "plan_id": self.plan_id,
            "result_summary": self.result_summary,
            "validation": (
                self.validation.to_dict() if self.validation else None
            ),
            "transition_to": (
                self.transition_to.value if self.transition_to else None
            ),
            "revision_pending": self.revision_pending,
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Trace:
        return cls(
            id=data["id"],
            kind=data["kind"],
            request_summary=data.get("request_summary", ""),
            context=dict(data.get("context") or {}),
            stage=LifecycleStage(data["stage"]),
            status=ActionStatus(data["status"]),
            dod=DoD.from_dict(data.get("dod") or {}),
            started_at=_parse_datetime(data["started_at"]),
            completed_at=_parse_datetime(data["completed_at"]),
            provenance=Provenance.from_dict(data["provenance"]),
            plan_id=data.get("plan_id"),
            result_summary=data.get("result_summary"),
            validation=(
                ValidationResult.from_dict(data["validation"])
                if data.get("validation")
                else None
            ),
            transition_to=(
                LifecycleStage(data["transition_to"])
                if data.get("transition_to")
                else None
            ),
            revision_pending=bool(data.get("revision_pending", False)),
            reason=data.get("reason", ""),
        )


def truncate_repr(value: Any, max_length: int) -> str:
    s = repr(value)
    if max_length <= 0:
        return ""
    if len(s) <= max_length:
        return s
    if max_length <= 3:
        return s[:max_length]
    return s[: max_length - 3] + "..."


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def _to_yaml_safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_to_yaml_safe(x) for x in value]
    if isinstance(value, dict):
        return {str(k): _to_yaml_safe(v) for k, v in value.items()}
    return repr(value)
