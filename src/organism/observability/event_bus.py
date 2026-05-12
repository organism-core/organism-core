from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

from organism.observability.settings import EventBusSettings
from organism.provenance import Provenance


@dataclass
class Event:
    type: str
    payload: dict[str, Any]
    timestamp: datetime
    provenance: Provenance | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "payload": dict(self.payload),
            "timestamp": self.timestamp.isoformat(),
            "provenance": (
                self.provenance.to_dict() if self.provenance else None
            ),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Event:
        prov_data = data.get("provenance")
        return cls(
            type=data["type"],
            payload=dict(data.get("payload") or {}),
            timestamp=_parse_datetime(data["timestamp"]),
            provenance=Provenance.from_dict(prov_data) if prov_data else None,
        )

    @classmethod
    def now(
        cls,
        type: str,
        payload: dict[str, Any] | None = None,
        provenance: Provenance | None = None,
    ) -> Event:
        return cls(
            type=type,
            payload=dict(payload or {}),
            timestamp=datetime.now(timezone.utc),
            provenance=provenance,
        )


HandlerCallable = Callable[[Event], None]


class EventBus:
    def __init__(self, settings: EventBusSettings | None = None) -> None:
        self.settings = settings or EventBusSettings()
        self._handlers: dict[str, dict[str, HandlerCallable]] = {}
        self._wildcard_handlers: dict[str, HandlerCallable] = {}
        self._next_id = 0

    def subscribe(
        self, event_type: str, handler: HandlerCallable
    ) -> str:
        sub_id = self._allocate_id()
        self._handlers.setdefault(event_type, {})[sub_id] = handler
        return sub_id

    def subscribe_all(self, handler: HandlerCallable) -> str:
        sub_id = self._allocate_id()
        self._wildcard_handlers[sub_id] = handler
        return sub_id

    def unsubscribe(self, sub_id: str) -> None:
        for handlers_dict in self._handlers.values():
            handlers_dict.pop(sub_id, None)
        self._wildcard_handlers.pop(sub_id, None)

    def publish(self, event: Event) -> None:
        if not self.settings.enabled:
            return
        targeted = self._handlers.get(event.type, {})
        for handler in list(targeted.values()):
            self._call_handler(handler, event)
        for handler in list(self._wildcard_handlers.values()):
            self._call_handler(handler, event)

    def _call_handler(
        self, handler: HandlerCallable, event: Event
    ) -> None:
        try:
            handler(event)
        except Exception:
            if self.settings.handler_error_action == "raise":
                raise

    def _allocate_id(self) -> str:
        sub_id = f"sub_{self._next_id}"
        self._next_id += 1
        return sub_id


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)
