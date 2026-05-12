from __future__ import annotations

from typing import Any

from organism.observability.trace import Trace
from organism.orchestrator.types import ActionStatus

OTEL_STATUS_OK = "OK"
OTEL_STATUS_ERROR = "ERROR"
OTEL_STATUS_UNSET = "UNSET"


def trace_to_otel_span(trace: Trace) -> dict[str, Any]:
    attrs: dict[str, Any] = {
        "gen_ai.operation.name": trace.kind,
        "gen_ai.system": trace.provenance.author,
        "organism.lifecycle.stage": trace.stage.value,
        "organism.action.status": trace.status.value,
        "organism.dod.confidence": trace.dod.confidence,
        "organism.dod.criteria_count": len(trace.dod.criteria),
        "organism.revision_pending": trace.revision_pending,
    }
    if trace.plan_id:
        attrs["organism.plan_id"] = trace.plan_id
    if trace.validation is not None:
        attrs["organism.validation.score"] = trace.validation.score
        attrs["organism.validation.all_satisfied"] = (
            trace.validation.all_satisfied
        )
    if trace.transition_to is not None:
        attrs["organism.transition.to_stage"] = trace.transition_to.value
    if trace.reason:
        attrs["organism.reason"] = trace.reason

    return {
        "name": f"organism.execute.{trace.kind}",
        "kind": "INTERNAL",
        "trace_id": trace.id,
        "start_time": trace.started_at.isoformat(),
        "end_time": trace.completed_at.isoformat(),
        "status": {"code": _otel_status_code(trace)},
        "attributes": attrs,
        "events": [],
    }


def _otel_status_code(trace: Trace) -> str:
    if trace.status == ActionStatus.APPLIED:
        if trace.validation is not None and not trace.validation.all_satisfied:
            return OTEL_STATUS_ERROR
        return OTEL_STATUS_OK
    if trace.status == ActionStatus.DENIED:
        return OTEL_STATUS_ERROR
    return OTEL_STATUS_UNSET
