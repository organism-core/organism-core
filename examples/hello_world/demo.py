"""Hello-world demo — the simplest possible pipeline walk.

Single effector, single entity, one propose-approve-apply cycle.
Shows the DoD-Recherche engine and the validator side by side: how
declarative criteria in the entity frontmatter become a machine-
assessable result after ``act()``.

Two run modes:

* **Deterministic** — without ``ANTHROPIC_API_KEY`` in the environment.
  The qualitative criterion ``friendly_tone`` uses the ``self_check``
  evaluator; the effector self-attests friendliness. Demo is always
  green, no setup friction, no network calls.

* **LLM-judge** — with ``ANTHROPIC_API_KEY`` set. ``friendly_tone``
  switches to the ``llm_judge`` evaluator; an Anthropic Claude call
  decides whether the greeting is actually friendly. This is the
  pattern's real selling point: a qualitative criterion validated by
  an LLM, gated by deterministic criteria first."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from organism.dod import (
    Criterion,
    DoDEngine,
    DoDEngineSettings,
    DoDValidator,
    EvaluationContext,
    ValidationResult,
    default_sources,
)
from organism.dod.types import DoD
from organism.lessons import LessonsAggregator, LessonsStore
from organism.lifecycle import (
    LifecycleManager,
    LifecycleSettings,
    LifecycleStore,
)
from organism.memory import Entity, EntityStore
from organism.observability import EventBus, TraceStore
from organism.orchestrator import ActionOrchestrator
from organism.plan_gate import PlanGate, PlanStore

from examples.hello_world.effector import HelloGreeter

KIND = "greet_user"
ENTITY_ID = "world"
PrintFn = Callable[[str], None]


@dataclass
class DemoSummary:
    mode: str
    greeting: str
    score: float
    all_satisfied: bool
    criteria_results: list[tuple[str, bool, str]]


class _ContextualValidator(DoDValidator):
    """``DoDValidator`` that carries a default ``EvaluationContext``.

    The orchestrator calls ``validator.validate(dod, result)`` without
    a context kwarg, so any LLM-judge / self-check callable has to be
    injected here. A consumer that wires real LLM judges would likely
    do the same; the demo keeps it inline for visibility."""

    def __init__(
        self, default_context: EvaluationContext | None = None
    ) -> None:
        super().__init__()
        self._default_context = default_context or EvaluationContext()

    def validate(
        self,
        dod: DoD,
        result: dict[str, Any],
        *,
        context: EvaluationContext | None = None,
    ) -> ValidationResult:
        return super().validate(
            dod, result, context=context or self._default_context
        )


def _build_anthropic_judge(api_key: str) -> Callable[..., tuple[bool, str]]:
    """Return a ``(criterion, actual, result) -> (ok, reason)`` callable.

    Lazy-imports the ``anthropic`` SDK so the demo runs without the
    dependency when no API key is set. Uses Claude Haiku 4.5 — fast
    and cheap for short qualitative checks. The judge sees the full
    greeting text (not just ``actual``) so it can assess tone."""
    from anthropic import Anthropic  # type: ignore[import-not-found]

    client = Anthropic(api_key=api_key)

    def judge(
        criterion: Criterion, actual: Any, result: dict[str, Any]
    ) -> tuple[bool, str]:
        greeting = result.get("greeting", "")
        prompt = (
            "You are a strict tone reviewer. Decide whether the "
            "greeting below is friendly and welcoming.\n\n"
            f"Greeting: {greeting!r}\n\n"
            "Answer in exactly one word: YES or NO. No punctuation, "
            "no explanation."
        )
        message = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=8,
            messages=[{"role": "user", "content": prompt}],
        )
        verdict = message.content[0].text.strip().upper()  # type: ignore[union-attr]
        if verdict.startswith("YES"):
            return True, "llm_judge: YES"
        return False, f"llm_judge: {verdict!r}"

    return judge


def _entity_frontmatter(
    use_llm_judge: bool,
) -> dict[str, Any]:
    """Build the entity frontmatter with the right evaluator hint.

    The DoD lives in the entity profile; the evaluator switch decides
    how each criterion is checked after ``act()``. ``mentions_name``
    and ``length`` are deterministic (rule); ``friendly_tone`` is the
    qualitative one that can route to either path."""
    tone_evaluator = "llm_judge" if use_llm_judge else "self_check"
    return {
        "type": "greeting",
        "dod": {
            "criteria": [
                {
                    "name": "mentions_name",
                    "expected": True,
                    "weight": 1.0,
                },
                {
                    "name": "length",
                    "expected": "5..200",
                    "weight": 0.5,
                },
                {
                    "name": "friendly_tone",
                    "expected": True,
                    "weight": 0.8,
                    "evaluator": tone_evaluator,
                },
            ]
        },
    }


def run_demo(
    output_dir: Path,
    print_fn: PrintFn = print,
    *,
    api_key: str | None = None,
) -> DemoSummary:
    api_key = api_key if api_key is not None else os.environ.get(
        "ANTHROPIC_API_KEY", ""
    )
    use_llm = bool(api_key)

    print_fn("")
    print_fn("=" * 62)
    print_fn("  hello_world -- minimal DoD pipeline walk")
    print_fn(
        "  Mode: "
        + ("LLM judge (Anthropic Claude)" if use_llm else "deterministic (no API key)")
    )
    print_fn("=" * 62)
    print_fn("")

    # ---- Setup: minimal store wiring ----
    print_fn("[SETUP]")
    entity_store = EntityStore(output_dir / "entities")
    plan_store = PlanStore(output_dir / "plans")
    lifecycle_store = LifecycleStore(output_dir / "lifecycle")
    lessons_store = LessonsStore(output_dir / "lessons")
    trace_store = TraceStore(output_dir / "traces")

    bus = EventBus()
    aggregator = LessonsAggregator(store=lessons_store, event_bus=bus)
    sources = default_sources(
        entity_store=entity_store, lesson_aggregator=aggregator
    )
    engine = DoDEngine(
        sources=sources,
        settings=DoDEngineSettings(threshold=0.5),
    )

    # The validator carries the LLM callable if we have one.
    eval_ctx = EvaluationContext(
        llm_judge=_build_anthropic_judge(api_key) if use_llm else None
    )
    validator = _ContextualValidator(default_context=eval_ctx)

    plan_gate = PlanGate(store=plan_store)
    lifecycle = LifecycleManager(
        store=lifecycle_store,
        settings=LifecycleSettings(initial_stage="proposed"),
    )
    orchestrator = ActionOrchestrator(
        engine=engine,
        validator=validator,
        plan_gate=plan_gate,
        lifecycle=lifecycle,
        trace_store=trace_store,
        lessons_aggregator=aggregator,
        event_bus=bus,
    )
    print_fn(f"  Stores in {output_dir}")
    print_fn("  Engine: default 6-source star, threshold=0.5")
    print_fn(
        "  Validator: "
        + ("llm_judge enabled" if use_llm else "deterministic only")
    )
    print_fn("")

    # ---- Seeding: one entity with the DoD in its frontmatter ----
    print_fn("[SEEDING]")
    frontmatter = _entity_frontmatter(use_llm_judge=use_llm)
    entity_store.write(
        ENTITY_ID,
        Entity(
            frontmatter=frontmatter,
            body="A simple greeting target. See dod.criteria for the contract.",
        ),
    )
    criteria = frontmatter["dod"]["criteria"]
    print_fn(f"  entity={ENTITY_ID!r}, {len(criteria)} criteria:")
    for c in criteria:
        ev = c.get("evaluator", "rule")
        print_fn(
            f"    - {c['name']:<16} expected={c['expected']!r:<12} "
            f"weight={c['weight']}  evaluator={ev}"
        )
    print_fn("")

    # ---- One pipeline walk: propose -> approve -> apply ----
    print_fn("[PIPELINE]")
    effector = HelloGreeter(attest_friendly=True)
    request = "Adopter"

    propose_result = orchestrator.execute(
        effector,
        kind=KIND,
        request=request,
        context={"entity_id": ENTITY_ID},
    )
    print_fn(
        f"  execute(request={request!r}) -> "
        f"status={propose_result.status.value}, "
        f"plan={propose_result.plan.id[:8] if propose_result.plan else '-'}..."
    )

    plan_id = propose_result.plan.id  # type: ignore[union-attr]
    plan_gate.approve(plan_id, decided_by="adopter", reason="looks good")
    print_fn("  plan_gate.approve(...)")

    apply_result = orchestrator.apply_approved_plan(plan_id, effector)
    print_fn(
        f"  apply_approved_plan() -> "
        f"status={apply_result.status.value}, "
        f"score={apply_result.validation.score:.2f}"
    )
    print_fn("")

    # ---- Detailed validation breakdown ----
    print_fn("[VALIDATION]")
    print_fn(f"  greeting: {apply_result.result['greeting']!r}")
    print_fn(
        f"  all_satisfied={apply_result.validation.all_satisfied}, "
        f"score={apply_result.validation.score:.2f}"
    )
    for cr in apply_result.validation.criterion_results:
        mark = "[OK] " if cr.satisfied else "[FAIL]"
        reason = cr.reason or "satisfied"
        print_fn(f"    {mark} {cr.name:<16} {reason}")
    print_fn("")

    # ---- Take-aways ----
    print_fn("[NOTES]")
    if use_llm:
        print_fn(
            "  - The `friendly_tone` criterion was decided by an "
            "Anthropic Claude call,"
        )
        print_fn(
            "    not by the effector. The effector cannot game it."
        )
    else:
        print_fn(
            "  - The `friendly_tone` criterion is currently a self-"
            "check (effector attests)."
        )
        print_fn(
            "    Set ANTHROPIC_API_KEY to switch it to llm_judge "
            "(see README)."
        )
    print_fn(
        "  - Two deterministic criteria (`mentions_name`, `length`) "
        "always gate the result"
    )
    print_fn(
        "    first. The qualitative criterion is the cherry on top."
    )
    print_fn("")

    return DemoSummary(
        mode="llm_judge" if use_llm else "deterministic",
        greeting=apply_result.result["greeting"],
        score=apply_result.validation.score,
        all_satisfied=apply_result.validation.all_satisfied,
        criteria_results=[
            (cr.name, cr.satisfied, cr.reason)
            for cr in apply_result.validation.criterion_results
        ],
    )
