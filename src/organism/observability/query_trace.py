"""Query-side trace + persistence.

Separate from the action-side ``Trace`` because the schemas diverge:
``Trace`` carries criteria / validation / lifecycle-transitions,
``QueryTrace`` carries only request / result / latency / status. Mixing
them would force one of them to grow optional-everywhere fields.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

from organism.query.types import QueryStatus

QUERY_TRACE_FILE_SUFFIX = ".yaml"


@dataclass
class QueryTrace:
    id: str
    kind: str
    timestamp: datetime
    caller: str
    request_repr: str
    result_repr: str
    latency_ms: float
    status: QueryStatus
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "timestamp": self.timestamp.isoformat(),
            "caller": self.caller,
            "request_repr": self.request_repr,
            "result_repr": self.result_repr,
            "latency_ms": self.latency_ms,
            "status": self.status.value,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QueryTrace:
        return cls(
            id=data["id"],
            kind=data["kind"],
            timestamp=_parse_datetime(data["timestamp"]),
            caller=data["caller"],
            request_repr=data["request_repr"],
            result_repr=data["result_repr"],
            latency_ms=float(data["latency_ms"]),
            status=QueryStatus(data["status"]),
            error=data.get("error", ""),
        )


class QueryTraceStore:
    """File-backed query-trace storage, one YAML per trace."""

    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)

    def write(self, trace: QueryTrace) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        path = self._path_for(trace.id)
        path.write_text(
            yaml.safe_dump(
                trace.to_dict(),
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False,
            ),
            encoding="utf-8",
        )

    def read(self, trace_id: str) -> QueryTrace:
        path = self._path_for(trace_id)
        if not path.exists():
            raise FileNotFoundError(f"QueryTrace {trace_id!r} not found")
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return QueryTrace.from_dict(data)

    def exists(self, trace_id: str) -> bool:
        return self._path_for(trace_id).exists()

    def list(
        self,
        *,
        kind: str | None = None,
        limit: int = 100,
    ) -> list[QueryTrace]:
        """Returns up to ``limit`` traces, newest first."""
        if not self.root.exists():
            return []
        traces: list[QueryTrace] = []
        for path in self.root.glob(f"*{QUERY_TRACE_FILE_SUFFIX}"):
            if not path.is_file():
                continue
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            trace = QueryTrace.from_dict(data)
            if kind is not None and trace.kind != kind:
                continue
            traces.append(trace)
        # Stable order: timestamp desc, then id desc as tie-breaker so
        # traces written within the same clock-resolution-window get a
        # deterministic ordering instead of YAML-glob-iteration order.
        traces.sort(key=lambda t: (t.timestamp, t.id), reverse=True)
        return traces[:limit]

    def _path_for(self, trace_id: str) -> Path:
        return self.root / f"{trace_id}{QUERY_TRACE_FILE_SUFFIX}"


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    return datetime.fromisoformat(value)
