"""UI-facing event adapter on top of the internal EventBus.

The internal ``EventBus`` carries everything (lifecycle transitions,
plan-gate decisions, trace writes, lesson recordings, ...). A UI
typically only cares about a normalized subset with consistent shape
and a precomputed ``severity`` so it can drive notifications without
re-parsing payloads.

``UIEventStream`` subscribes to the underlying bus and re-emits a
``UIEvent`` to its subscribers. It does not store events — consumers
own buffering, persistence, and routing.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable

from organism.observability.event_bus import Event, EventBus

SEVERITY_INFO = "info"
SEVERITY_WARNING = "warning"
SEVERITY_CRITICAL = "critical"

# Internal-bus event types the Cockpit translates by default.
EVENT_PLAN_PROPOSED = "plan_proposed"
EVENT_LIFECYCLE_TRANSITION = "lifecycle_transition"
EVENT_LESSON_RECORDED = "lesson_recorded"
EVENT_TRACE_RECORDED = "trace_recorded"
EVENT_QUERY_RECORDED = "query_recorded"


@dataclass
class UIEvent:
    type: str
    kind: str                    # the effector-kind the event concerns
    timestamp: str
    summary: str                 # one-line, human-readable
    severity: str                # info | warning | critical
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_bus_event(cls, event: Event) -> UIEvent:
        payload = dict(event.payload)
        kind = str(payload.get("kind", ""))
        summary, severity = _summarize(event.type, payload)
        return cls(
            type=event.type,
            kind=kind,
            timestamp=event.timestamp.isoformat(),
            summary=summary,
            severity=severity,
            payload=payload,
        )


UIHandler = Callable[[UIEvent], None]


class UIEventStream:
    """Adapter: subscribes to an ``EventBus`` and re-emits ``UIEvent``s
    to UI-side handlers.

    Use ``subscribe(event_types, handler)`` with a list of internal
    event types you care about (or ``None`` for all). One handler can
    be registered for many type-filters; ``unsubscribe(sub_id)`` removes
    the binding by the returned id.
    """

    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self._handlers: dict[str, tuple[set[str] | None, UIHandler]] = {}
        self._bus_sub_id = bus.subscribe_all(self._on_bus_event)
        self._next_id = 0

    def subscribe(
        self,
        event_types: list[str] | None,
        handler: UIHandler,
    ) -> str:
        sub_id = self._allocate_id()
        type_filter = set(event_types) if event_types else None
        self._handlers[sub_id] = (type_filter, handler)
        return sub_id

    def unsubscribe(self, sub_id: str) -> None:
        self._handlers.pop(sub_id, None)

    def close(self) -> None:
        """Detach from the underlying bus. Call when the UI shuts down."""
        self.bus.unsubscribe(self._bus_sub_id)
        self._handlers.clear()

    def _on_bus_event(self, event: Event) -> None:
        ui_event = UIEvent.from_bus_event(event)
        for type_filter, handler in list(self._handlers.values()):
            if type_filter is not None and ui_event.type not in type_filter:
                continue
            try:
                handler(ui_event)
            except Exception:
                # Stream is best-effort; drop the failing handler call
                # so a buggy UI doesn't break others.
                continue

    def _allocate_id(self) -> str:
        sub_id = f"ui_sub_{self._next_id}"
        self._next_id += 1
        return sub_id


def _summarize(event_type: str, payload: dict[str, Any]) -> tuple[str, str]:
    kind = payload.get("kind", "?")

    if event_type == EVENT_PLAN_PROPOSED:
        proposed_by = payload.get("proposed_by", "?")
        if proposed_by == "orchestrator:revision_escalation":
            return (
                f"plan proposed (revision escalation, kind={kind})",
                SEVERITY_WARNING,
            )
        return f"plan proposed (kind={kind}, by={proposed_by})", SEVERITY_INFO

    if event_type == EVENT_LIFECYCLE_TRANSITION:
        from_stage = payload.get("from_stage", "?")
        to_stage = payload.get("to_stage", "?")
        reason = payload.get("reason", "")
        is_demote = reason.startswith("demote") if isinstance(reason, str) else False
        severity = SEVERITY_WARNING if is_demote else SEVERITY_INFO
        return (
            f"lifecycle: {from_stage} -> {to_stage} (kind={kind})",
            severity,
        )

    if event_type == EVENT_LESSON_RECORDED:
        observation = payload.get("observation", "")
        short = (
            observation[:60] + "…"
            if isinstance(observation, str) and len(observation) > 60
            else observation
        )
        return f"lesson recorded (kind={kind}): {short}", SEVERITY_INFO

    if event_type == EVENT_TRACE_RECORDED:
        status = payload.get("status", "?")
        severity = (
            SEVERITY_WARNING
            if status in ("denied", "needs_clarification")
            else SEVERITY_INFO
        )
        return f"trace recorded (kind={kind}, status={status})", severity

    if event_type == EVENT_QUERY_RECORDED:
        status = payload.get("status", "?")
        caller = payload.get("caller", "?")
        latency = payload.get("latency_ms", 0.0)
        severity = (
            SEVERITY_WARNING if status == "error" else SEVERITY_INFO
        )
        return (
            f"query recorded (kind={kind}, caller={caller}, "
            f"status={status}, {latency:.1f}ms)",
            severity,
        )

    return f"event: {event_type} (kind={kind})", SEVERITY_INFO
