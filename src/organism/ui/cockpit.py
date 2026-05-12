"""Cockpit — the headless "Wesen" that hovers over the tools.

A Cockpit instance reads from the stores (EntityStore, PlanGate,
LifecycleManager, LessonsAggregator, optional TraceStore) and emits
typed view-dataclasses. It writes nothing. Any UI framework — React,
Vue, terminal-TUI, IDE plugin — consumes the views; the Cockpit does
not care.

The Cockpit is *not* an orchestrator. It performs no actions, gates
no decisions, runs no effectors. It is purely a query/observer layer.
For the action side, see ``organism.orchestrator.ActionOrchestrator``.
"""

from __future__ import annotations

from typing import Any

from organism.dod.engine import DoDEngine
from organism.lessons.aggregator import LessonsAggregator
from organism.lifecycle.manager import LifecycleManager
from organism.lifecycle.types import LifecycleStage
from organism.observability.query_trace import QueryTraceStore
from organism.plan_gate.gate import PlanGate
from organism.plan_gate.types import PlanStatus
from organism.ui.settings import CockpitSettings
from organism.ui.views import (
    DoDView,
    DriftView,
    EffectorSummaryView,
    PlanApprovalView,
    QueryTraceView,
)


class Cockpit:
    """Headless UI Wesen: queries state, returns view dataclasses."""

    def __init__(
        self,
        *,
        engine: DoDEngine,
        plan_gate: PlanGate,
        lifecycle: LifecycleManager,
        lessons: LessonsAggregator,
        query_trace_store: QueryTraceStore | None = None,
        settings: CockpitSettings | None = None,
    ) -> None:
        self.engine = engine
        self.plan_gate = plan_gate
        self.lifecycle = lifecycle
        self.lessons = lessons
        self.query_trace_store = query_trace_store
        self.settings = settings or CockpitSettings()

    # ---------- DoD inspection

    def inspect_dod(
        self,
        *,
        request: Any,
        context: dict[str, Any] | None = None,
    ) -> DoDView:
        """Derive a DoD via the engine and render it as a DoDView.

        Does not run any effector. Useful for previewing what an
        effector would be judged against before triggering an action.
        """
        dod = self.engine.derive(request, context or {})
        return DoDView.from_dod(dod)

    # ---------- Plan approval

    def pending_plans(
        self,
        *,
        kind: str | None = None,
        include_resolved: bool | None = None,
    ) -> list[PlanApprovalView]:
        """Return open plans (PROPOSED by default) for human review.

        ``include_resolved`` overrides ``settings.show_resolved_plans``
        when given. Capped at ``settings.plan_list_max_items``.
        """
        show_resolved = (
            include_resolved
            if include_resolved is not None
            else self.settings.show_resolved_plans
        )
        if show_resolved:
            plans = self.plan_gate.list(kind=kind)
        else:
            plans = self.plan_gate.list(kind=kind, status=PlanStatus.PROPOSED)

        plans = plans[: self.settings.plan_list_max_items]
        # Pre-compute diff hints once: count of prior proposed plans of
        # the same kind (rough "how often does this happen?" cue).
        prior_counts_by_kind: dict[str, int] = {}
        if plans:
            for p in self.plan_gate.list(status=None):
                if p.status not in (
                    PlanStatus.APPLIED,
                    PlanStatus.REJECTED,
                    PlanStatus.EXPIRED,
                ):
                    continue
                prior_counts_by_kind[p.kind] = (
                    prior_counts_by_kind.get(p.kind, 0) + 1
                )

        views: list[PlanApprovalView] = []
        for plan in plans:
            diff_hints: list[str] = []
            prior_count = prior_counts_by_kind.get(plan.kind, 0)
            if prior_count > 0:
                diff_hints.append(
                    f"{prior_count} prior decided plans of this kind"
                )
            if plan.proposed_by == "orchestrator:revision_escalation":
                failed = plan.payload.get("failed_criteria") or []
                if failed:
                    diff_hints.append(
                        "escalated via revision strategy; "
                        f"{len(failed)} criteria failed"
                    )
            views.append(
                PlanApprovalView.from_plan(
                    plan,
                    payload_repr_max_length=(
                        self.settings.payload_repr_max_length
                    ),
                    diff_hints=diff_hints,
                )
            )
        return views

    # ---------- Drift

    def drift(self, kind: str) -> DriftView:
        """Return the drift view for a single ``kind``."""
        state = self.lifecycle.get_state(kind)
        return DriftView.from_state(
            state,
            self.lifecycle.settings,
            trend_window=self.settings.trend_window,
            drift_warning_band=self.settings.drift_warning_band,
        )

    def drift_overview(self) -> list[DriftView]:
        """All known ``kind`` states, sorted by drift_warning desc then
        by current_stage_index asc (warnings first, lower stages first).
        """
        kinds = self.lifecycle.store.list_kinds()
        views = [self.drift(k) for k in kinds]
        views.sort(
            key=lambda v: (not v.drift_warning, v.current_stage_index)
        )
        return views

    # ---------- Effector summary

    def summary(self) -> list[EffectorSummaryView]:
        """One row per known ``kind`` — high-level dashboard listing."""
        rows: list[EffectorSummaryView] = []
        for kind in self.lifecycle.store.list_kinds():
            state = self.lifecycle.get_state(kind)
            outcomes = state.recent_outcomes
            avg = (
                sum(o.score for o in outcomes) / len(outcomes)
                if outcomes
                else 0.0
            )
            pending = len(
                self.plan_gate.list(kind=kind, status=PlanStatus.PROPOSED)
            )
            lessons = len(self.lessons.store.list(kind=kind))
            drift = self.drift(kind)
            rows.append(
                EffectorSummaryView(
                    kind=kind,
                    current_stage=state.stage.value,
                    avg_score=avg,
                    outcomes_count=len(outcomes),
                    pending_plans=pending,
                    lessons_count=lessons,
                    drift_warning=drift.drift_warning,
                )
            )
        rows.sort(key=lambda r: (not r.drift_warning, r.kind))
        return rows

    # ---------- Query traces (read-only path)

    def recent_queries(
        self,
        *,
        kind: str | None = None,
        limit: int = 20,
    ) -> list[QueryTraceView]:
        """Return the most recent ``QueryTrace`` records, newest first.

        Returns ``[]`` when no ``QueryTraceStore`` was wired into the
        Cockpit at construction time — query-side observability is opt-in.
        """
        if self.query_trace_store is None:
            return []
        traces = self.query_trace_store.list(kind=kind, limit=limit)
        return [QueryTraceView.from_trace(t) for t in traces]

    # ---------- Stage introspection

    def known_kinds(self) -> list[str]:
        return self.lifecycle.store.list_kinds()

    def stage_for(self, kind: str) -> LifecycleStage:
        return self.lifecycle.get_stage(kind)
