from __future__ import annotations

from dataclasses import dataclass

from organism.settings import SettingsBase, register_settings


@register_settings("trace_store")
@dataclass
class TraceStoreSettings(SettingsBase):
    enabled: bool = True
    summary_max_length: int = 500

    def __post_init__(self) -> None:
        if self.summary_max_length < 0:
            raise ValueError(
                "summary_max_length must be >= 0, "
                f"got {self.summary_max_length}"
            )


@register_settings("event_bus")
@dataclass
class EventBusSettings(SettingsBase):
    enabled: bool = True
    handler_error_action: str = "continue"

    def __post_init__(self) -> None:
        if self.handler_error_action not in ("continue", "raise"):
            raise ValueError(
                "handler_error_action must be 'continue' or 'raise', "
                f"got {self.handler_error_action!r}"
            )


@register_settings("langfuse")
@dataclass
class LangfuseSettings(SettingsBase):
    enabled: bool = False
    endpoint_url: str = ""
    public_key: str = ""
