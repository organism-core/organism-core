from __future__ import annotations

from dataclasses import dataclass

from organism.settings import SettingsBase, register_settings


@register_settings("query_runner")
@dataclass
class QueryRunnerSettings(SettingsBase):
    """Tunables for the QueryRunner. All admin-UI-visible.

    record_traces             write a QueryTrace per execute() — only
                              effective if a QueryTraceStore is wired
    truncate_request_repr     bytes-cap for the trace's request_repr;
                              keeps the trace from becoming a data db
    truncate_result_repr      bytes-cap for the trace's result_repr
    emit_events               publish ``EVENT_QUERY_RECORDED`` on the
                              EventBus (only effective if a bus is wired)
    """

    record_traces: bool = True
    truncate_request_repr: int = 200
    truncate_result_repr: int = 500
    emit_events: bool = False

    def __post_init__(self) -> None:
        if self.truncate_request_repr < 16:
            raise ValueError(
                "truncate_request_repr must be >= 16, "
                f"got {self.truncate_request_repr}"
            )
        if self.truncate_result_repr < 16:
            raise ValueError(
                "truncate_result_repr must be >= 16, "
                f"got {self.truncate_result_repr}"
            )
