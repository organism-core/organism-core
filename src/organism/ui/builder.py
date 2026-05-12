"""CockpitBuilder — fluent assembly for the headless UI Wesen.

The ``Cockpit`` constructor takes six required + optional collaborators
(engine, plan_gate, lifecycle, lessons, query_trace_store, settings).
Wiring all of them at call-sites becomes noisy quickly; the builder
provides a fluent API:

    cockpit = (
        CockpitBuilder()
        .with_engine(engine)
        .with_plan_gate(plan_gate)
        .with_lifecycle(lifecycle)
        .with_lessons(aggregator)
        .with_query_trace_store(query_store)   # optional
        .with_settings(CockpitSettings(...))    # optional
        .build()
    )

``build()`` validates that the four required collaborators are present
and raises ``CockpitBuilderError`` otherwise. The builder is single-use
(once ``build()`` has run, calling it again returns a fresh Cockpit
with the same wiring — useful for repeated test fixtures).
"""

from __future__ import annotations

from organism.dod.engine import DoDEngine
from organism.lessons.aggregator import LessonsAggregator
from organism.lifecycle.manager import LifecycleManager
from organism.observability.query_trace import QueryTraceStore
from organism.plan_gate.gate import PlanGate
from organism.ui.cockpit import Cockpit
from organism.ui.settings import CockpitSettings


class CockpitBuilderError(ValueError):
    """Raised when ``CockpitBuilder.build()`` is called with missing
    required collaborators."""


class CockpitBuilder:
    def __init__(self) -> None:
        self._engine: DoDEngine | None = None
        self._plan_gate: PlanGate | None = None
        self._lifecycle: LifecycleManager | None = None
        self._lessons: LessonsAggregator | None = None
        self._query_trace_store: QueryTraceStore | None = None
        self._settings: CockpitSettings | None = None

    def with_engine(self, engine: DoDEngine) -> CockpitBuilder:
        self._engine = engine
        return self

    def with_plan_gate(self, plan_gate: PlanGate) -> CockpitBuilder:
        self._plan_gate = plan_gate
        return self

    def with_lifecycle(
        self, lifecycle: LifecycleManager
    ) -> CockpitBuilder:
        self._lifecycle = lifecycle
        return self

    def with_lessons(
        self, lessons: LessonsAggregator
    ) -> CockpitBuilder:
        self._lessons = lessons
        return self

    def with_query_trace_store(
        self, store: QueryTraceStore | None
    ) -> CockpitBuilder:
        self._query_trace_store = store
        return self

    def with_settings(self, settings: CockpitSettings) -> CockpitBuilder:
        self._settings = settings
        return self

    def build(self) -> Cockpit:
        missing: list[str] = []
        if self._engine is None:
            missing.append("engine")
        if self._plan_gate is None:
            missing.append("plan_gate")
        if self._lifecycle is None:
            missing.append("lifecycle")
        if self._lessons is None:
            missing.append("lessons")
        if missing:
            raise CockpitBuilderError(
                "CockpitBuilder.build() missing required collaborators: "
                + ", ".join(missing)
            )
        return Cockpit(
            engine=self._engine,
            plan_gate=self._plan_gate,
            lifecycle=self._lifecycle,
            lessons=self._lessons,
            query_trace_store=self._query_trace_store,
            settings=self._settings,
        )
