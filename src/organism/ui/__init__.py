"""Headless UI layer for organism-core.

Pure data contracts and a query Cockpit — no HTML, no CSS, no framework.
Consumers (React, Vue, terminal-TUI, IDE plugin, Slack bot, ...) render
the views however they want; the Skelett owns the data shape.

    Cockpit              query/observer Wesen over the existing stores
    DoDView              schema for rendering a derived DoD
    PlanApprovalView     schema for rendering a pending plan with the
                         richer ApprovalAction descriptors
    DriftView            schema for rendering effector quality-trend
    EffectorSummaryView  one-line dashboard row per ``kind``
    UIEvent              normalized event for UI notifications
    UIEventStream        adapter on EventBus that re-emits UIEvents
    CockpitSettings      tunables (payload truncation, trend window,
                         drift-warning band, list cap)
"""

from organism.ui.builder import CockpitBuilder, CockpitBuilderError
from organism.ui.cockpit import Cockpit
from organism.ui.events import (
    EVENT_LESSON_RECORDED,
    EVENT_LIFECYCLE_TRANSITION,
    EVENT_PLAN_PROPOSED,
    EVENT_QUERY_RECORDED,
    EVENT_TRACE_RECORDED,
    SEVERITY_CRITICAL,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    UIEvent,
    UIEventStream,
)
from organism.ui.settings import CockpitSettings
from organism.ui.views import (
    ApprovalAction,
    CriterionView,
    DoDView,
    DriftView,
    EffectorSummaryView,
    PlanApprovalView,
    QueryTraceView,
)

__all__ = [
    "ApprovalAction",
    "Cockpit",
    "CockpitBuilder",
    "CockpitBuilderError",
    "CockpitSettings",
    "CriterionView",
    "DoDView",
    "DriftView",
    "EVENT_LESSON_RECORDED",
    "EVENT_LIFECYCLE_TRANSITION",
    "EVENT_PLAN_PROPOSED",
    "EVENT_QUERY_RECORDED",
    "EVENT_TRACE_RECORDED",
    "EffectorSummaryView",
    "PlanApprovalView",
    "QueryTraceView",
    "SEVERITY_CRITICAL",
    "SEVERITY_INFO",
    "SEVERITY_WARNING",
    "UIEvent",
    "UIEventStream",
]
