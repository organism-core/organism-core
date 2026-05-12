from __future__ import annotations

from pathlib import Path
from typing import Any

from organism.dod import (
    Criterion,
    DoD,
    DoDEngine,
    DoDValidator,
    SourceContribution,
)
from organism.dod.sources.lessons import CONTEXT_KEY_KIND, LessonsSource
from organism.lessons import LessonsAggregator, LessonsStore
from organism.lifecycle import (
    LifecycleManager,
    LifecycleSettings,
    LifecycleStore,
)
from organism.orchestrator import (
    ActionOrchestrator,
    ActionStatus,
    OrchestratorSettings,
)
from organism.plan_gate import PlanGate, PlanStore


class _BaseSource:
    def __init__(
        self,
        name: str,
        criteria: list[Criterion],
        confidence_delta: float = 1.0,
    ) -> None:
        self.name = name
        self._criteria = criteria
        self._confidence_delta = confidence_delta

    def contribute(
        self,
        request: Any,
        context: dict[str, Any],
        current: DoD,
    ) -> SourceContribution:
        return SourceContribution(
            source_name=self.name,
            criteria=[
                Criterion(
                    name=c.name,
                    expected=c.expected,
                    weight=c.weight,
                    evaluator=c.evaluator,
                )
                for c in self._criteria
            ],
            confidence_delta=self._confidence_delta,
        )


class _Effector:
    name = "ef"

    def __init__(self, results: list[Any]) -> None:
        self._results = list(results)
        self.act_count = 0

    def pre_load(self, ctx):
        return ctx

    def define_done(self, request, context):
        return {}

    def act(self, request):
        idx = min(self.act_count, len(self._results) - 1)
        self.act_count += 1
        return self._results[idx]

    def upstream(self, kind, payload):
        pass

    def gate(self, action):
        return True


def _build(
    tmp_path: Path,
    *,
    base_criteria: list[Criterion],
    effector_results: list[Any],
    max_attempts: int = 2,
    initial_stage: str = "autonomous",
) -> tuple[ActionOrchestrator, _Effector, LessonsAggregator]:
    base_source = _BaseSource(
        name="base",
        criteria=base_criteria,
        confidence_delta=1.0,
    )
    aggregator = LessonsAggregator(store=LessonsStore(tmp_path / "lessons"))
    lessons_source = LessonsSource(aggregator=aggregator)

    engine = DoDEngine(sources=[base_source, lessons_source])
    validator = DoDValidator()
    plan_gate = PlanGate(store=PlanStore(tmp_path / "plans"))
    lifecycle = LifecycleManager(
        store=LifecycleStore(tmp_path / "lifecycle"),
        settings=LifecycleSettings(initial_stage=initial_stage),
    )
    orchestrator = ActionOrchestrator(
        engine=engine,
        validator=validator,
        plan_gate=plan_gate,
        lifecycle=lifecycle,
        lessons_aggregator=aggregator,
        settings=OrchestratorSettings(
            autonomous_max_revision_attempts=max_attempts
        ),
    )
    return orchestrator, _Effector(effector_results), aggregator


# Revision skipped when validation passes immediately


def test_no_revision_when_validation_passes(tmp_path: Path):
    orchestrator, effector, aggregator = _build(
        tmp_path,
        base_criteria=[Criterion(name="ok", expected=True)],
        effector_results=[{"ok": True}],
    )
    result = orchestrator.execute(effector, kind="k", request="x")
    assert result.status == ActionStatus.APPLIED
    assert result.revision_attempts == 0
    assert result.revision_pending is False
    assert effector.act_count == 1
    assert aggregator.store.list() == []


# Revision succeeds after 1 retry


def test_revision_succeeds_on_retry(tmp_path: Path):
    orchestrator, effector, aggregator = _build(
        tmp_path,
        base_criteria=[Criterion(name="ok", expected=True)],
        effector_results=[{"ok": False}, {"ok": True}],
    )
    result = orchestrator.execute(effector, kind="k", request="x")
    assert result.status == ActionStatus.APPLIED
    assert result.revision_attempts == 1
    assert result.revision_pending is False
    assert result.validation.all_satisfied is True
    assert effector.act_count == 2
    # One lesson recorded for the failed attempt
    assert len(aggregator.store.list()) == 1


# Revision fails after max_attempts


def test_revision_pending_after_max_attempts(tmp_path: Path):
    orchestrator, effector, aggregator = _build(
        tmp_path,
        base_criteria=[Criterion(name="ok", expected=True)],
        effector_results=[{"ok": False}],
        max_attempts=2,
    )
    result = orchestrator.execute(effector, kind="k", request="x")
    assert result.status == ActionStatus.APPLIED
    assert result.revision_attempts == 2
    assert result.revision_pending is True
    assert result.validation.all_satisfied is False
    # 1 initial + 2 revisions = 3 act calls
    assert effector.act_count == 3
    # 2 lessons recorded (one per failed attempt before retry)
    assert len(aggregator.store.list()) == 2


# Max attempts = 0 disables revision


def test_max_attempts_zero_disables_revision(tmp_path: Path):
    orchestrator, effector, aggregator = _build(
        tmp_path,
        base_criteria=[Criterion(name="ok", expected=True)],
        effector_results=[{"ok": False}],
        max_attempts=0,
    )
    result = orchestrator.execute(effector, kind="k", request="x")
    assert result.revision_attempts == 0
    assert result.revision_pending is True
    assert effector.act_count == 1
    assert aggregator.store.list() == []


# Revision only fires in AUTONOMOUS stage


def test_no_revision_in_checked_stage(tmp_path: Path):
    orchestrator, effector, aggregator = _build(
        tmp_path,
        base_criteria=[Criterion(name="ok", expected=True)],
        effector_results=[{"ok": False}],
        initial_stage="checked",
    )
    result = orchestrator.execute(effector, kind="k", request="x")
    assert result.revision_attempts == 0
    assert result.revision_pending is False  # not AUTONOMOUS
    assert effector.act_count == 1
    assert aggregator.store.list() == []


# Without aggregator, AUTONOMOUS just flags revision_pending


def test_no_aggregator_skips_revision(tmp_path: Path):
    base_source = _BaseSource(
        name="base",
        criteria=[Criterion(name="ok", expected=True)],
    )
    engine = DoDEngine(sources=[base_source])
    validator = DoDValidator()
    plan_gate = PlanGate(store=PlanStore(tmp_path / "plans"))
    lifecycle = LifecycleManager(
        store=LifecycleStore(tmp_path / "lifecycle"),
        settings=LifecycleSettings(initial_stage="autonomous"),
    )
    orchestrator = ActionOrchestrator(
        engine=engine,
        validator=validator,
        plan_gate=plan_gate,
        lifecycle=lifecycle,
        lessons_aggregator=None,  # no aggregator
    )
    effector = _Effector(results=[{"ok": False}])
    result = orchestrator.execute(effector, kind="k", request="x")
    assert result.revision_attempts == 0
    assert result.revision_pending is True
    assert effector.act_count == 1


# Revision-recorded lesson has expected fields


def test_revision_lesson_has_orchestrator_provenance(tmp_path: Path):
    orchestrator, effector, aggregator = _build(
        tmp_path,
        base_criteria=[Criterion(name="ok", expected=True)],
        effector_results=[{"ok": False}, {"ok": True}],
    )
    orchestrator.execute(effector, kind="k", request="x")
    lessons = aggregator.store.list()
    assert len(lessons) == 1
    lesson = lessons[0]
    assert lesson.kind == "k"
    assert "AUTONOMOUS revision" in lesson.observation
    assert lesson.provenance.author == "orchestrator"
    assert lesson.provenance.source == "dod_failure"


# Lesson-Loop: revision lessons carry the failed criteria so the next
# DoD-Recherche picks them up via LessonsSource.


def test_revision_lesson_carries_failed_criteria(tmp_path: Path):
    orchestrator, effector, aggregator = _build(
        tmp_path,
        base_criteria=[
            Criterion(name="ok", expected=True, weight=1.0),
            Criterion(name="other", expected=42, weight=2.0),
        ],
        effector_results=[
            {"ok": False, "other": 42},  # only "ok" fails
            {"ok": True, "other": 42},
        ],
    )
    orchestrator.execute(effector, kind="k", request="x")
    lesson = aggregator.store.list()[0]
    assert len(lesson.criteria_hint) == 1
    failed = lesson.criteria_hint[0]
    assert failed.name == "ok"
    assert failed.expected is True
    assert failed.source == "dod_failure"
    # weight halved by REVISION_LESSON_CRITERION_WEIGHT_FACTOR=0.5
    assert failed.weight == 0.5


def test_revision_lesson_preserves_evaluator_per_criterion(tmp_path: Path):
    orchestrator, effector, aggregator = _build(
        tmp_path,
        base_criteria=[
            Criterion(
                name="self_attest",
                expected=True,
                evaluator="self_check",
            ),
        ],
        effector_results=[{"self_attest": False}, {"self_attest": True}],
    )
    orchestrator.execute(effector, kind="k", request="x")
    lesson = aggregator.store.list()[0]
    assert lesson.criteria_hint[0].evaluator == "self_check"


def test_revision_lesson_context_pattern_uses_configured_keys(tmp_path: Path):
    base_source = _BaseSource(
        name="base",
        criteria=[Criterion(name="ok", expected=True)],
        confidence_delta=1.0,
    )
    aggregator = LessonsAggregator(store=LessonsStore(tmp_path / "lessons"))
    lessons_source = LessonsSource(aggregator=aggregator)
    engine = DoDEngine(sources=[base_source, lessons_source])
    plan_gate = PlanGate(store=PlanStore(tmp_path / "plans"))
    lifecycle = LifecycleManager(
        store=LifecycleStore(tmp_path / "lifecycle"),
        settings=LifecycleSettings(initial_stage="autonomous"),
    )
    orchestrator = ActionOrchestrator(
        engine=engine,
        validator=DoDValidator(),
        plan_gate=plan_gate,
        lifecycle=lifecycle,
        lessons_aggregator=aggregator,
        settings=OrchestratorSettings(
            autonomous_max_revision_attempts=1,
            lesson_context_keys=["domain", "subtype"],
        ),
    )
    effector = _Effector(results=[{"ok": False}, {"ok": True}])
    orchestrator.execute(
        effector,
        kind="k",
        request="x",
        context={"domain": "alpha", "subtype": "beta", "irrelevant": "z"},
    )
    lesson = aggregator.store.list()[0]
    assert lesson.context_pattern == {"domain": "alpha", "subtype": "beta"}


def test_lesson_loop_closes_across_actions(tmp_path: Path):
    """End-to-end: action 1 fails → lesson written; action 2 picks lesson
    back up via LessonsSource and the failed criterion appears in its DoD
    before the action runs."""

    base_source = _BaseSource(
        name="base",
        criteria=[Criterion(name="primary", expected=True, weight=1.0)],
        confidence_delta=0.5,  # below threshold so engine continues
    )
    aggregator = LessonsAggregator(store=LessonsStore(tmp_path / "lessons"))
    lessons_source = LessonsSource(aggregator=aggregator)
    engine = DoDEngine(sources=[base_source, lessons_source])
    plan_gate = PlanGate(store=PlanStore(tmp_path / "plans"))
    lifecycle = LifecycleManager(
        store=LifecycleStore(tmp_path / "lifecycle"),
        settings=LifecycleSettings(initial_stage="autonomous"),
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
    )

    # Action 1: fails on "primary" (initial + 1 retry, both fail)
    effector1 = _Effector(results=[{"primary": False}])
    orchestrator.execute(effector1, kind="k", request="x1")
    lessons = aggregator.store.list()
    assert len(lessons) == 1
    learned_lesson = lessons[0]
    assert learned_lesson.provenance.source == "dod_failure"
    assert learned_lesson.criteria_hint[0].name == "primary"
    # The criterion stored in the lesson preserves its dod_failure origin.
    assert learned_lesson.criteria_hint[0].source == "dod_failure"

    # Action 2 (re-derive DoD): lesson surfaces back via LessonsSource.
    derived_dod = engine.derive("x2", {"kind": "k"})
    primary_entries = [
        c for c in derived_dod.criteria if c.name == "primary"
    ]
    # base contributed "primary" once; lessons source re-injects "primary"
    # one more time after merging the learned lesson.
    assert len(primary_entries) >= 2
    # Engine's merge stamps source=<source_name>; one of the entries comes
    # from the lessons source.
    assert any(c.source == "lessons" for c in primary_entries)
    # Lessons source is recorded in the DoD's provenance ledger.
    assert "primary" in derived_dod._provenance.get("lessons", [])
