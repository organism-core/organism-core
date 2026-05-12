from __future__ import annotations

from typing import Any

from organism.observability.otel import trace_to_otel_span
from organism.observability.settings import LangfuseSettings
from organism.observability.trace import Trace


class LangfuseAdapter:
    """Stub Langfuse-Adapter.

    Phase 4.3 holds posted spans in memory for inspection and tests.
    Phase 6+ replaces post() with real HTTP-push to the Langfuse endpoint
    (settings.endpoint_url + settings.public_key).
    """

    def __init__(self, settings: LangfuseSettings | None = None) -> None:
        self.settings = settings or LangfuseSettings()
        self.posted_spans: list[dict[str, Any]] = []

    def post(self, span: dict[str, Any]) -> None:
        if not self.settings.enabled:
            return
        self.posted_spans.append(dict(span))

    def post_trace(self, trace: Trace) -> None:
        self.post(trace_to_otel_span(trace))

    def flush(self) -> None:
        return None

    def reset(self) -> None:
        self.posted_spans.clear()
