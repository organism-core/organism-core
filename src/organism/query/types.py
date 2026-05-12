"""Result and status types for the read-only query path.

Schlank gegen ``ActionResult``: no plan, no DoD, no validation, no
lifecycle transition. Reads either return data or raise; the runner
captures latency and an optional trace id.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class QueryStatus(str, Enum):
    OK = "ok"
    ERROR = "error"


@dataclass
class QueryResult:
    status: QueryStatus
    kind: str
    caller: str
    result: Any = None
    error: str = ""
    latency_ms: float = 0.0
    trace_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "kind": self.kind,
            "caller": self.caller,
            "result": self.result,
            "error": self.error,
            "latency_ms": self.latency_ms,
            "trace_id": self.trace_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QueryResult:
        return cls(
            status=QueryStatus(data["status"]),
            kind=data["kind"],
            caller=data["caller"],
            result=data.get("result"),
            error=data.get("error", ""),
            latency_ms=float(data.get("latency_ms", 0.0)),
            trace_id=data.get("trace_id"),
        )
