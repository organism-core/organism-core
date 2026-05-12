from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from organism.dod import (
    DoDEngine,
    DoDEngineSettings,
    DoDValidator,
    default_sources,
)
from organism.lessons import LessonsAggregator, LessonsStore
from organism.lifecycle import (
    LifecycleManager,
    LifecycleSettings,
    LifecycleStage,
    LifecycleStore,
)
from organism.memory import Entity, EntityStore
from organism.observability import Event, EventBus, TraceStore
from organism.orchestrator import (
    ActionOrchestrator,
    OrchestratorSettings,
)
from organism.plan_gate import PlanGate, PlanStore

from examples.tax_lite.effector import TaxReturnValidator
from examples.tax_lite.entities import ENTITIES

KIND = "validate_tax_return"
PrintFn = Callable[[str], None]


@dataclass
class DemoSummary:
    entities_seeded: int = 0
    actions_executed: int = 0
    plans_proposed: int = 0
    plans_applied: int = 0
    traces_recorded: int = 0
    lessons_recorded: int = 0
    events_captured: int = 0
    transitions_observed: int = 0
    final_stage: str = ""
    event_types: dict[str, int] = field(default_factory=dict)


def run_demo(
    output_dir: Path,
    print_fn: PrintFn = print,
) -> DemoSummary:
    summary = DemoSummary()

    print_fn("")
    print_fn("==============================================================")
    print_fn("  tax_lite -- DoD-Pipeline-Walk")
    print_fn("  3 synthetische Mandanten, kind=validate_tax_return")
    print_fn("==============================================================")
    print_fn("")

    # ---- Setup ----
    print_fn("[SETUP]")
    entity_store = EntityStore(output_dir / "entities")
    plan_store = PlanStore(output_dir / "plans")
    lifecycle_store = LifecycleStore(output_dir / "lifecycle")
    lessons_store = LessonsStore(output_dir / "lessons")
    trace_store = TraceStore(output_dir / "traces")

    bus = EventBus()
    captured_events: list[Event] = []
    bus.subscribe_all(captured_events.append)

    aggregator = LessonsAggregator(store=lessons_store, event_bus=bus)
    sources = default_sources(
        entity_store=entity_store, lesson_aggregator=aggregator
    )
    engine = DoDEngine(
        sources=sources,
        settings=DoDEngineSettings(threshold=0.5),
    )
    plan_gate = PlanGate(store=plan_store)
    lifecycle = LifecycleManager(
        store=lifecycle_store,
        settings=LifecycleSettings(
            initial_stage="proposed",
            promote_after_n=3,
            promote_score_threshold=0.9,
            demote_after_n=2,
            demote_score_threshold=0.5,
            window_size=10,
        ),
    )
    orchestrator = ActionOrchestrator(
        engine=engine,
        validator=DoDValidator(),
        plan_gate=plan_gate,
        lifecycle=lifecycle,
        trace_store=trace_store,
        lessons_aggregator=aggregator,
        event_bus=bus,
        settings=OrchestratorSettings(autonomous_max_revision_attempts=2),
    )
    print_fn(f"  Stores in {output_dir}")
    print_fn("  Engine: 6 Sources (default), Threshold=0.5")
    print_fn("  Lifecycle: initial=proposed, promote_after_n=3")
    print_fn("")

    # ---- Seeding ----
    print_fn("[SEEDING]")
    for entity_id, frontmatter in ENTITIES.items():
        entity_store.write(
            entity_id, Entity(frontmatter=frontmatter, body="")
        )
        summary.entities_seeded += 1
        criteria_count = len(frontmatter["dod"]["criteria"])
        print_fn(
            f"  {entity_id} "
            f"({frontmatter['type']}/{frontmatter['client_type']}, "
            f"{criteria_count} Kriterien)"
        )
    print_fn("")

    # ---- Step 1: PROPOSED stage ----
    print_fn("[STEP 1] Stage PROPOSED -- propose -> approve -> apply")
    pass_effector = TaxReturnValidator(
        return_map={
            "client-042-2024": {
                "all_income_recorded": True,
                "tax_class_in_range": 3,
                "deductions_plausible": 1500,
            },
            "client-088-2024": {
                "all_income_recorded": True,
                "tax_class_in_range": 4,
            },
            "gmbh-fischer-2024": {
                "ust_id_present": True,
                "revenue_above_threshold": 50000,
            },
        }
    )

    propose_result = orchestrator.execute(
        pass_effector,
        kind=KIND,
        request="client-042-2024",
        context={"entity_id": "client-042-2024"},
    )
    summary.actions_executed += 1
    if propose_result.plan:
        summary.plans_proposed += 1
        plan_id = propose_result.plan.id
        print_fn(
            f"  execute() -> status={propose_result.status.value}, "
            f"plan={plan_id[:8]}..."
        )
        plan_gate.approve(
            plan_id, decided_by="steuerberater_a", reason="ok"
        )
        print_fn("  plan_gate.approve(...)")
        apply_result = orchestrator.apply_approved_plan(
            plan_id, pass_effector
        )
        summary.actions_executed += 1
        summary.plans_applied += 1
        if apply_result.transition:
            summary.transitions_observed += 1
        print_fn(
            f"  apply_approved_plan() -> "
            f"status={apply_result.status.value}, "
            f"score={apply_result.validation.score:.2f}"
        )
    print_fn("")

    # ---- Step 2: CHECKED stage with promotion ----
    print_fn("[STEP 2] Stage CHECKED -- set_stage + 3 actions -> promotion")
    lifecycle.set_stage(
        KIND, LifecycleStage.CHECKED, reason="demo: skip to checked"
    )

    for entity_id in (
        "client-042-2024",
        "client-088-2024",
        "gmbh-fischer-2024",
    ):
        result = orchestrator.execute(
            pass_effector,
            kind=KIND,
            request=entity_id,
            context={"entity_id": entity_id},
        )
        summary.actions_executed += 1
        if result.transition:
            summary.transitions_observed += 1
            marker = (
                f" -> TRANSITION {result.transition.from_stage.value} "
                f"-> {result.transition.to_stage.value}"
            )
        else:
            marker = ""
        print_fn(
            f"  {entity_id}: status={result.status.value}, "
            f"score={result.validation.score:.2f}{marker}"
        )
    print_fn(
        f"  Lifecycle nach Step 2: stage={lifecycle.get_stage(KIND).value}"
    )
    print_fn("")

    # ---- Step 3: AUTONOMOUS stage with failing effector ----
    print_fn(
        "[STEP 3] Stage AUTONOMOUS -- failing effector -> revision-loop"
    )
    lifecycle.set_stage(
        KIND,
        LifecycleStage.AUTONOMOUS,
        reason="demo: skip to autonomous",
    )

    fail_effector = TaxReturnValidator(
        return_map={
            "client-042-2024": {
                "all_income_recorded": False,
                "tax_class_in_range": 3,
            },
        }
    )
    autonomous_result = orchestrator.execute(
        fail_effector,
        kind=KIND,
        request="client-042-2024",
        context={"entity_id": "client-042-2024"},
    )
    summary.actions_executed += 1
    print_fn(
        f"  execute() -> status={autonomous_result.status.value}, "
        f"score={autonomous_result.validation.score:.2f}, "
        f"revision_attempts={autonomous_result.revision_attempts}, "
        f"revision_pending={autonomous_result.revision_pending}"
    )
    print_fn(
        f"  -> {autonomous_result.revision_attempts} Revision-Lessons "
        "aufgezeichnet"
    )
    print_fn("")

    # ---- Step 4: Manual HITL lesson ----
    print_fn("[STEP 4] Manuelle HITL-Lesson")
    aggregator.record_lesson(
        kind=KIND,
        observation=(
            "GmbH-Mandanten benoetigen ust_id-Check vor Abschluss"
        ),
        criteria_hint=[],
        confidence_delta=0.1,
        context_pattern={"client_type": "gmbh"},
    )
    print_fn("  aggregator.record_lesson(...)")
    print_fn("")

    # ---- Summary ----
    print_fn("[SUMMARY]")
    summary.traces_recorded = len(trace_store.list())
    summary.lessons_recorded = len(lessons_store.list())
    summary.events_captured = len(captured_events)
    summary.final_stage = lifecycle.get_stage(KIND).value
    for event in captured_events:
        summary.event_types[event.type] = (
            summary.event_types.get(event.type, 0) + 1
        )

    print_fn(f"  Mandanten geseedet:     {summary.entities_seeded}")
    print_fn(f"  Aktionen ausgefuehrt:   {summary.actions_executed}")
    print_fn(f"  Plans vorgeschlagen:    {summary.plans_proposed}")
    print_fn(f"  Plans applied:          {summary.plans_applied}")
    print_fn(f"  Traces aufgezeichnet:   {summary.traces_recorded}")
    print_fn(f"  Lessons aufgezeichnet:  {summary.lessons_recorded}")
    print_fn(f"  Events captured:        {summary.events_captured}")
    print_fn(f"  Transitions beobachtet: {summary.transitions_observed}")
    print_fn(f"  Finale Stage:           {summary.final_stage}")
    print_fn("")
    print_fn("  Event-Typen:")
    for event_type in sorted(summary.event_types):
        print_fn(f"    {event_type}: {summary.event_types[event_type]}")
    print_fn("")

    return summary
