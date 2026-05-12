"""Read-only counterpart to ``ActionOrchestrator``.

Wraps a Querier in trace + latency. Writes nothing user-facing — only
optional ``QueryTrace`` records. No plans, no DoD, no lifecycle, no
lessons. For action-side, see ``organism.orchestrator.ActionOrchestrator``.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from organism.provenance import Provenance
from organism.query.querier import Querier
from organism.query.settings import QueryRunnerSettings
from organism.query.types import QueryResult, QueryStatus

if TYPE_CHECKING:
    from organism.observability.event_bus import EventBus
    from organism.observability.query_trace import QueryTraceStore

EVENT_QUERY_RECORDED = "query_recorded"


class QueryRunner:
    def __init__(
        self,
        *,
        trace_store: "QueryTraceStore | None" = None,
        event_bus: "EventBus | None" = None,
        settings: QueryRunnerSettings | None = None,
    ) -> None:
        self.trace_store = trace_store
        self.event_bus = event_bus
        self.settings = settings or QueryRunnerSettings()

    def execute(
        self,
        querier: Querier,
        *,
        kind: str,
        request: Any,
        context: dict[str, Any] | None = None,
        caller: str = "anonymous",
    ) -> QueryResult:
        ctx = querier.pre_load(dict(context or {}))
        ctx.setdefault("kind", kind)

        started = time.monotonic()
        status = QueryStatus.OK
        error = ""
        result: Any = None
        try:
            result = querier.query(request)
        except Exception as exc:
            status = QueryStatus.ERROR
            error = f"{type(exc).__name__}: {exc}"
        latency_ms = (time.monotonic() - started) * 1000.0

        trace_id = self._maybe_record_trace(
            kind=kind,
            caller=caller,
            request=request,
            result=result,
            error=error,
            latency_ms=latency_ms,
            status=status,
        )

        if trace_id is not None and self.settings.emit_events:
            self._publish_event(
                trace_id=trace_id,
                kind=kind,
                caller=caller,
                status=status,
                latency_ms=latency_ms,
            )

        return QueryResult(
            status=status,
            kind=kind,
            caller=caller,
            result=result,
            error=error,
            latency_ms=latency_ms,
            trace_id=trace_id,
        )

    def _maybe_record_trace(
        self,
        *,
        kind: str,
        caller: str,
        request: Any,
        result: Any,
        error: str,
        latency_ms: float,
        status: QueryStatus,
    ) -> str | None:
        if self.trace_store is None or not self.settings.record_traces:
            return None

        from organism.observability.query_trace import QueryTrace

        trace = QueryTrace(
            id=str(uuid.uuid4()),
            kind=kind,
            timestamp=datetime.now(timezone.utc),
            caller=caller,
            request_repr=_truncate(request, self.settings.truncate_request_repr),
            result_repr=_truncate(result, self.settings.truncate_result_repr),
            latency_ms=latency_ms,
            status=status,
            error=error,
        )
        self.trace_store.write(trace)
        return trace.id

    def _publish_event(
        self,
        *,
        trace_id: str,
        kind: str,
        caller: str,
        status: QueryStatus,
        latency_ms: float,
    ) -> None:
        if self.event_bus is None:
            return
        from organism.observability.event_bus import Event

        self.event_bus.publish(
            Event.now(
                type=EVENT_QUERY_RECORDED,
                payload={
                    "trace_id": trace_id,
                    "kind": kind,
                    "caller": caller,
                    "status": status.value,
                    "latency_ms": latency_ms,
                },
                provenance=Provenance.now(
                    author="query_runner", source=EVENT_QUERY_RECORDED
                ),
            )
        )


def _truncate(value: Any, max_length: int) -> str:
    text = repr(value)
    if len(text) <= max_length:
        return text
    return text[: max_length - 1] + "…"
