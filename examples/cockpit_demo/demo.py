"""Cockpit-Demo — shows the headless UI Wesen at work.

Sets up a minimal action environment (engine + plan-gate + lifecycle +
lessons + event-bus), drives a few actions through it to populate
state, and then exercises every Cockpit query to print what a UI
generator would receive. No HTML, no framework — just typed dicts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from organism.adapter import BaseEffector
from organism.dod import (
    REVISION_ESCALATE_TO_HUMAN,
    Criterion,
    DoD,
    DoDEngine,
    DoDEngineSettings,
    DoDValidator,
    SourceContribution,
)
from organism.lessons import LessonsAggregator, LessonsStore
from organism.lifecycle import (
    LifecycleManager,
    LifecycleSettings,
    LifecycleStage,
    LifecycleStore,
)
from organism.observability import Event, EventBus
from organism.orchestrator import (
    ActionOrchestrator,
    OrchestratorSettings,
)
from organism.plan_gate import PlanGate, PlanStore
from organism.ui import (
    Cockpit,
    CockpitSettings,
    UIEvent,
    UIEventStream,
)

KIND_A = "task_alpha"
KIND_B = "task_beta"
KIND_C = "task_gamma"
PrintFn = Callable[[str], None]


# ---------- Effector + Source for the demo


class _FlexEffector(BaseEffector):
    """Synthetic effector that returns from a request->dict map."""

    name = "flex_effector"

    def __init__(self, return_map: dict[str, Any]) -> None:
        self.return_map = dict(return_map)

    def define_done(self, request, context):
        return {}

    def act(self, request):
        return self.return_map.get(request, {"ok": False})


class _StaticDoDSource:
    """One-shot source that returns a fixed DoD per ``kind``."""

    name = "static"

    def __init__(self, by_kind: dict[str, list[Criterion]]) -> None:
        self.by_kind = by_kind

    def contribute(self, request, context, current):
        kind = context.get("kind")
        criteria = self.by_kind.get(kind or "", [])
        return SourceContribution(
            source_name=self.name,
            criteria=list(criteria),
            confidence_delta=1.0 if criteria else 0.0,
        )


# ---------- Summary


@dataclass
class CockpitDemoSummary:
    kinds_seeded: int = 0
    actions_executed: int = 0
    pending_plans_count: int = 0
    drift_warnings: int = 0
    summary_rows: int = 0
    ui_events_captured: int = 0
    ui_event_severities: dict[str, int] = field(default_factory=dict)


# ---------- Demo


def run_demo(
    output_dir: Path,
    print_fn: PrintFn = print,
) -> CockpitDemoSummary:
    summary = CockpitDemoSummary()

    print_fn("")
    print_fn("==============================================================")
    print_fn("  cockpit_demo -- Headless UI Wesen ueber dem Orchestrator")
    print_fn("==============================================================")
    print_fn("")

    # ---- Setup ----
    print_fn("[SETUP]")
    plan_gate = PlanGate(store=PlanStore(output_dir / "plans"))
    lifecycle = LifecycleManager(
        store=LifecycleStore(output_dir / "lifecycle"),
        settings=LifecycleSettings(
            initial_stage="checked",
            promote_after_n=3,
            promote_score_threshold=0.9,
            demote_after_n=2,
            demote_score_threshold=0.5,
            window_size=10,
        ),
    )
    bus = EventBus()
    aggregator = LessonsAggregator(
        store=LessonsStore(output_dir / "lessons"), event_bus=bus
    )

    # Three distinct DoDs per kind to differentiate drift behavior later.
    # KIND_C's DoD has two weighted criteria where the effector fulfills
    # only the primary one — yielding a weighted score of 0.55, just
    # above the demote threshold (0.5) and inside the drift band (0.05).
    dods_by_kind = {
        KIND_A: [
            Criterion(name="success", expected=True, weight=1.0),
        ],
        KIND_B: [
            Criterion(name="quality", expected=True, weight=1.0),
            Criterion(
                name="needs_review",
                expected=True,
                weight=0.5,
                revision_strategy=REVISION_ESCALATE_TO_HUMAN,
            ),
        ],
        KIND_C: [
            Criterion(name="primary", expected=True, weight=0.55),
            Criterion(name="secondary", expected=True, weight=0.45),
        ],
    }
    source = _StaticDoDSource(dods_by_kind)
    engine = DoDEngine(
        sources=[source], settings=DoDEngineSettings(threshold=0.5)
    )
    orchestrator = ActionOrchestrator(
        engine=engine,
        validator=DoDValidator(),
        plan_gate=plan_gate,
        lifecycle=lifecycle,
        lessons_aggregator=aggregator,
        settings=OrchestratorSettings(
            autonomous_max_revision_attempts=1,
        ),
        event_bus=bus,
    )

    # The Cockpit is the headless Wesen.
    cockpit = Cockpit(
        engine=engine,
        plan_gate=plan_gate,
        lifecycle=lifecycle,
        lessons=aggregator,
        settings=CockpitSettings(
            payload_repr_max_length=80,
            trend_window=4,
            drift_warning_band=0.05,
        ),
    )

    # UIEventStream subscribed to the bus — collects UIEvents.
    ui_stream = UIEventStream(bus)
    captured_ui: list[UIEvent] = []
    ui_stream.subscribe(None, captured_ui.append)
    print_fn("  Cockpit + UIEventStream wired")
    print_fn("")

    # ---- Drive a few actions to populate state ----
    print_fn("[DRIVING ACTIONS]")

    # KIND_A — 3 successful → promotes from checked to routine
    effector_a = _FlexEffector(
        return_map={"r1": {"success": True}, "r2": {"success": True}, "r3": {"success": True}}
    )
    for r in ("r1", "r2", "r3"):
        orchestrator.execute(
            effector_a, kind=KIND_A, request=r, context={"kind": KIND_A}
        )
        summary.actions_executed += 1
    summary.kinds_seeded += 1

    # KIND_B — propose a plan (orchestrator stages it because escalate_to_human
    # criterion fails). We start KIND_B in autonomous to trigger escalation.
    lifecycle.set_stage(KIND_B, LifecycleStage.AUTONOMOUS, reason="demo")
    effector_b = _FlexEffector(
        return_map={"q1": {"quality": True, "needs_review": False}}
    )
    orchestrator.execute(
        effector_b, kind=KIND_B, request="q1", context={"kind": KIND_B}
    )
    summary.actions_executed += 1
    summary.kinds_seeded += 1

    # KIND_C — drift warning: two boundary-case actions. The effector
    # fulfills only the primary criterion; weighted score 0.55 sits just
    # above the demote threshold (0.5) and inside the drift band (0.05).
    # No demote fires (window-avg stays above 0.5), but the Cockpit's
    # drift_warning flag activates.
    effector_c = _FlexEffector(
        return_map={
            "p1": {"primary": True, "secondary": False},
            "p2": {"primary": True, "secondary": False},
        }
    )
    for r in ("p1", "p2"):
        orchestrator.execute(
            effector_c, kind=KIND_C, request=r, context={"kind": KIND_C}
        )
        summary.actions_executed += 1
    summary.kinds_seeded += 1

    print_fn(f"  Aktionen ausgefuehrt: {summary.actions_executed}")
    print_fn("")

    # ---- inspect_dod ----
    print_fn("[COCKPIT.inspect_dod]")
    dod_view = cockpit.inspect_dod(request="preview", context={"kind": KIND_B})
    print_fn(f"  kind={KIND_B}")
    print_fn(f"  criteria: {[c.name for c in dod_view.criteria]}")
    print_fn(f"  total_weight: {dod_view.total_weight}")
    print_fn(f"  evaluator_breakdown: {dod_view.evaluator_breakdown}")
    print_fn(
        f"  revision_strategy_summary: {dod_view.revision_strategy_summary}"
    )
    print_fn("")

    # ---- pending_plans ----
    print_fn("[COCKPIT.pending_plans]")
    plans = cockpit.pending_plans()
    summary.pending_plans_count = len(plans)
    print_fn(f"  open plans: {len(plans)}")
    for plan_view in plans:
        print_fn(
            f"    plan {plan_view.plan_id[:8]}... kind={plan_view.kind}"
        )
        print_fn(
            f"      proposed_by: {plan_view.proposed_by}"
        )
        if plan_view.is_revision_escalation:
            print_fn(
                f"      REVISION ESCALATION, failed: "
                f"{plan_view.failed_criteria}"
            )
        for action in plan_view.actions_available:
            print_fn(
                f"      action: id={action.id} severity={action.severity} "
                f"requires_reason={action.requires_reason}"
            )
        if plan_view.diff_hints:
            print_fn(f"      hints: {plan_view.diff_hints}")
    print_fn("")

    # ---- drift_overview ----
    print_fn("[COCKPIT.drift_overview]")
    drift_views = cockpit.drift_overview()
    for dv in drift_views:
        marker = "WARNING " if dv.drift_warning else "ok      "
        if dv.drift_warning:
            summary.drift_warnings += 1
        print_fn(
            f"  {marker} kind={dv.kind} stage={dv.current_stage} "
            f"avg={dv.avg_score:.2f} trend={dv.score_trend} "
            f"dist_demote={dv.distance_to_demote:+.2f}"
        )
    print_fn("")

    # ---- summary (dashboard rows) ----
    print_fn("[COCKPIT.summary]")
    rows = cockpit.summary()
    summary.summary_rows = len(rows)
    for row in rows:
        warn = "!" if row.drift_warning else " "
        print_fn(
            f"  {warn} {row.kind}: stage={row.current_stage} "
            f"avg={row.avg_score:.2f} pending_plans={row.pending_plans} "
            f"lessons={row.lessons_count}"
        )
    print_fn("")

    # ---- UI events captured ----
    print_fn("[UIEventStream]")
    summary.ui_events_captured = len(captured_ui)
    for ui_event in captured_ui:
        summary.ui_event_severities[ui_event.severity] = (
            summary.ui_event_severities.get(ui_event.severity, 0) + 1
        )
    print_fn(f"  ui_events captured: {summary.ui_events_captured}")
    print_fn(f"  severities: {summary.ui_event_severities}")
    print_fn("")

    # ---- JSON-ready output for one view ----
    print_fn("[JSON-Sample] (PlanApprovalView for a pending plan, if any)")
    if plans:
        sample = json.dumps(plans[0].to_dict(), indent=2, default=str)
        # Just print first 400 chars to keep demo output bounded.
        clipped = (
            sample
            if len(sample) <= 400
            else sample[:400] + "\n    ... (truncated)"
        )
        for line in clipped.splitlines():
            print_fn(f"  {line}")
    else:
        print_fn("  (no pending plans to render)")
    print_fn("")

    # ---- Summary ----
    print_fn("[SUMMARY]")
    print_fn(f"  kinds seeded:     {summary.kinds_seeded}")
    print_fn(f"  actions executed: {summary.actions_executed}")
    print_fn(f"  pending plans:    {summary.pending_plans_count}")
    print_fn(f"  drift warnings:   {summary.drift_warnings}")
    print_fn(f"  summary rows:     {summary.summary_rows}")
    print_fn(f"  ui events:        {summary.ui_events_captured}")
    print_fn("")

    ui_stream.close()
    return summary
