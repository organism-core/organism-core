"""Guard for the "Define your own effector" example in README.md.

Mirrors the README snippet line for line (prints replaced by asserts).
If this test breaks, the README example no longer compiles against the
real API — update both READMEs together with this file.
"""

from __future__ import annotations

from organism.adapter import BaseEffector
from organism.dod import (
    DoDEngine,
    DoDEngineSettings,
    DoDValidator,
    default_sources,
)
from organism.lifecycle import LifecycleManager, LifecycleStore
from organism.memory import Entity, EntityStore
from organism.orchestrator import ActionOrchestrator, ActionStatus
from organism.plan_gate import PlanGate, PlanStore


class GreetingEffector(BaseEffector):
    name = "greeting_effector"

    def define_done(self, request, context):
        return {}  # let the DoD engine derive the criteria

    def act(self, request):
        return {"greeting_present": True}


def test_readme_example_round_trip(tmp_path):
    entities = EntityStore(tmp_path / "entities")
    entities.write(
        "demo-entity",
        Entity(
            frontmatter={
                "dod": {
                    "criteria": [
                        {"name": "greeting_present", "expected": True}
                    ]
                },
            }
        ),
    )

    orchestrator = ActionOrchestrator(
        engine=DoDEngine(
            sources=default_sources(entity_store=entities),
            settings=DoDEngineSettings(threshold=0.5),
        ),
        validator=DoDValidator(),
        plan_gate=PlanGate(store=PlanStore(tmp_path / "plans")),
        lifecycle=LifecycleManager(store=LifecycleStore(tmp_path / "lifecycle")),
    )

    effector = GreetingEffector()
    result = orchestrator.execute(
        effector,
        kind="say_hello",
        request="hello",
        context={"entity_id": "demo-entity"},
    )
    assert result.status is ActionStatus.PROPOSED
    assert result.plan is not None

    orchestrator.plan_gate.approve(result.plan.id, decided_by="you")
    applied = orchestrator.apply_approved_plan(result.plan.id, effector)
    assert applied.status is ActionStatus.APPLIED
    assert applied.validation is not None
    assert applied.validation.score == 1.0
