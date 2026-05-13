from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from organism.adapter.effector import Effector
from organism.dod.engine import DoDEngine
from organism.dod.types import (
    REVISION_ESCALATE_TO_HUMAN,
    REVISION_RETRY_ALT_PARAMS,
    REVISION_ROLLBACK_AND_LOG,
    REVISION_STRATEGY_PRIORITY,
    Criterion,
    DoD,
)
from organism.dod.validator import DoDValidator, ValidationResult
from organism.lessons.aggregator import LessonsAggregator
from organism.lifecycle.manager import LifecycleManager
from organism.lifecycle.types import LifecycleStage
from organism.observability.event_bus import Event, EventBus
from organism.observability.settings import TraceStoreSettings
from organism.observability.store import TraceStore
from organism.observability.trace import Trace, truncate_repr
from organism.orchestrator.settings import (
    ON_DEFINITION_ABORT,
    ON_DEFINITION_ASK,
    ON_DEFINITION_PROCEED_WITH_WARNING,
    ON_FULFILLMENT_ABORT,
    ON_FULFILLMENT_RETRY,
    ON_FULFILLMENT_WARN,
    REVISION_LESSON_SOURCE,
    OrchestratorSettings,
)
from organism.orchestrator.types import (
    REVISION_OUTCOME_COMPLETED,
    REVISION_OUTCOME_ESCALATED,
    REVISION_OUTCOME_EXHAUSTED,
    REVISION_OUTCOME_FAILED,
    REVISION_OUTCOME_NONE,
    REVISION_OUTCOME_ROLLED_BACK,
    ActionResult,
    ActionStatus,
)
from organism.plan_gate.gate import PlanGate
from organism.plan_gate.types import PlanStatus
from organism.provenance import Provenance

EVENT_PLAN_PROPOSED = "plan_proposed"
EVENT_LIFECYCLE_TRANSITION = "lifecycle_transition"
EVENT_TRACE_RECORDED = "trace_recorded"


class ActionOrchestrator:
    def __init__(
        self,
        engine: DoDEngine,
        validator: DoDValidator,
        plan_gate: PlanGate,
        lifecycle: LifecycleManager,
        trace_store: TraceStore | None = None,
        trace_settings: TraceStoreSettings | None = None,
        lessons_aggregator: LessonsAggregator | None = None,
        settings: OrchestratorSettings | None = None,
        event_bus: EventBus | None = None,
    ) -> None:
        self.engine = engine
        self.validator = validator
        self.plan_gate = plan_gate
        self.lifecycle = lifecycle
        self.trace_store = trace_store
        self.trace_settings = trace_settings or TraceStoreSettings()
        self.lessons_aggregator = lessons_aggregator
        self.settings = settings or OrchestratorSettings()
        self.event_bus = event_bus

    def execute(
        self,
        effector: Effector,
        *,
        kind: str,
        request: Any,
        context: dict[str, Any] | None = None,
        proposed_by: str | None = None,
    ) -> ActionResult:
        started_at = _now()
        ctx = effector.pre_load(dict(context or {}))
        ctx["kind"] = kind
        dod = self.engine.derive(request, ctx)
        stage = self.lifecycle.get_stage(kind)

        unclear_warnings: list[str] = []
        proceed_despite_unclear = False
        if dod.clarification_needed:
            mode = self.settings.on_definition_unclear
            if mode == ON_DEFINITION_ABORT:
                result = ActionResult(
                    status=ActionStatus.DENIED,
                    dod=dod,
                    reason=(
                        "DoD undefined and on_definition_unclear=abort: "
                        + "; ".join(dod.clarification_needed)
                    ),
                )
            elif mode == ON_DEFINITION_PROCEED_WITH_WARNING:
                proceed_despite_unclear = True
                unclear_warnings.append(
                    "DoD-clarification-needed bypassed via "
                    "on_definition_unclear=proceed_with_warning: "
                    + "; ".join(dod.clarification_needed)
                )
                result = None  # falls through to stage dispatch below
            else:  # ON_DEFINITION_ASK (default)
                result = ActionResult(
                    status=ActionStatus.NEEDS_CLARIFICATION, dod=dod
                )
        else:
            result = None  # falls through to stage dispatch below

        if result is not None:
            pass
        elif stage == LifecycleStage.MANUAL:
            result = ActionResult(
                status=ActionStatus.MANUAL,
                dod=dod,
                reason="lifecycle stage is manual; system declined automation",
            )
        elif stage == LifecycleStage.PROPOSED:
            plan = self.plan_gate.propose(
                kind=kind,
                payload={"request": request, "context": ctx},
                dod=dod,
                proposed_by=_proposed_by(effector, proposed_by),
            )
            self._publish_event(
                EVENT_PLAN_PROPOSED,
                {
                    "plan_id": plan.id,
                    "kind": kind,
                    "proposed_by": plan.proposed_by,
                },
            )
            result = ActionResult(
                status=ActionStatus.PROPOSED, plan=plan, dod=dod
            )
        else:
            result = self._run_directly(
                effector=effector,
                kind=kind,
                request=request,
                ctx=ctx,
                dod=dod,
                stage=stage,
                plan_id=None,
            )

        if proceed_despite_unclear and unclear_warnings:
            result.warnings = list(result.warnings) + unclear_warnings

        self._publish_transition_event(kind, result)

        trace_id = self._record_trace(
            kind=kind,
            request=request,
            context=ctx,
            dod=result.dod or dod,
            stage=stage,
            result=result,
            started_at=started_at,
            effector=effector,
            proposed_by=proposed_by,
            source="orchestrator.execute",
        )
        if trace_id is not None:
            self._publish_event(
                EVENT_TRACE_RECORDED,
                {
                    "trace_id": trace_id,
                    "kind": kind,
                    "status": result.status.value,
                },
            )
        return result

    def apply_approved_plan(
        self,
        plan_id: str,
        effector: Effector,
    ) -> ActionResult:
        started_at = _now()
        plan = self.plan_gate.get(plan_id)
        if plan.status != PlanStatus.APPROVED:
            raise ValueError(
                f"Cannot apply plan {plan_id!r}: status is "
                f"{plan.status.value!r}, expected 'approved'"
            )

        request = plan.payload.get("request")

        action_descriptor = {
            "kind": plan.kind,
            "request": request,
            "plan_id": plan_id,
        }
        if not effector.gate(action_descriptor):
            result = ActionResult(
                status=ActionStatus.DENIED,
                plan=plan,
                dod=plan.dod,
                reason="effector.gate() returned False during apply",
            )
        else:
            action_result = effector.act(request)
            validation = self.validator.validate(plan.dod, action_result)
            threshold = self.settings.fulfillment_score_pass
            warnings: list[str] = []
            non_autonomous_outcome = ""
            if not validation.is_fulfilled(threshold):
                (
                    action_result,
                    validation,
                    non_autonomous_outcome,
                    warnings,
                ) = self._apply_fulfillment_policy(
                    effector=effector,
                    kind=plan.kind,
                    request=request,
                    ctx={"plan_id": plan_id},
                    dod=plan.dod,
                    result=action_result,
                    validation=validation,
                )
            applied_plan = self.plan_gate.apply(plan_id)
            _, transition = self.lifecycle.record_outcome(
                kind=plan.kind, plan_id=plan_id, score=validation.score
            )
            if non_autonomous_outcome == ON_FULFILLMENT_ABORT:
                result = ActionResult(
                    status=ActionStatus.DENIED,
                    plan=applied_plan,
                    result=action_result,
                    validation=validation,
                    transition=transition,
                    dod=plan.dod,
                    warnings=warnings,
                    reason="DoD-Verfehlung mit on_fulfillment_failed=abort.",
                )
            else:
                result = ActionResult(
                    status=ActionStatus.APPLIED,
                    plan=applied_plan,
                    result=action_result,
                    validation=validation,
                    transition=transition,
                    dod=plan.dod,
                    warnings=warnings,
                )

        self._publish_transition_event(plan.kind, result)

        stage = self.lifecycle.get_stage(plan.kind)
        trace_id = self._record_trace(
            kind=plan.kind,
            request=request,
            context={"plan_id": plan_id},
            dod=plan.dod,
            stage=stage,
            result=result,
            started_at=started_at,
            effector=effector,
            proposed_by=None,
            source="orchestrator.apply_approved_plan",
        )
        if trace_id is not None:
            self._publish_event(
                EVENT_TRACE_RECORDED,
                {
                    "trace_id": trace_id,
                    "kind": plan.kind,
                    "status": result.status.value,
                },
            )
        return result

    def _run_directly(
        self,
        *,
        effector: Effector,
        kind: str,
        request: Any,
        ctx: dict[str, Any],
        dod: DoD,
        stage: LifecycleStage,
        plan_id: str | None,
    ) -> ActionResult:
        action_descriptor = {"kind": kind, "request": request}
        if plan_id is not None:
            action_descriptor["plan_id"] = plan_id
        if not effector.gate(action_descriptor):
            return ActionResult(
                status=ActionStatus.DENIED,
                dod=dod,
                reason="effector.gate() returned False",
            )

        result = effector.act(request)
        validation = self.validator.validate(dod, result)

        threshold = self.settings.fulfillment_score_pass
        warnings: list[str] = []
        revision_attempts = 0
        revision_outcome = REVISION_OUTCOME_NONE
        escalation_plan = None
        non_autonomous_outcome: str = ""

        if (
            stage == LifecycleStage.AUTONOMOUS
            and self.lessons_aggregator
            and not validation.is_fulfilled(threshold)
        ):
            (
                dod,
                result,
                validation,
                revision_attempts,
                revision_outcome,
                escalation_plan,
            ) = self._run_revision_loop(
                effector=effector,
                kind=kind,
                request=request,
                ctx=ctx,
                dod=dod,
                result=result,
                validation=validation,
            )
        elif (
            stage != LifecycleStage.AUTONOMOUS
            and not validation.is_fulfilled(threshold)
        ):
            (
                result,
                validation,
                non_autonomous_outcome,
                warnings,
            ) = self._apply_fulfillment_policy(
                effector=effector,
                kind=kind,
                request=request,
                ctx=ctx,
                dod=dod,
                result=result,
                validation=validation,
            )

        _, transition = self.lifecycle.record_outcome(
            kind=kind, plan_id=plan_id, score=validation.score
        )

        revision_pending = (
            stage == LifecycleStage.AUTONOMOUS
            and not validation.is_fulfilled(threshold)
            and revision_outcome
            not in (
                REVISION_OUTCOME_ESCALATED,
                REVISION_OUTCOME_ROLLED_BACK,
                REVISION_OUTCOME_FAILED,
            )
        )

        if revision_outcome == REVISION_OUTCOME_ESCALATED:
            return ActionResult(
                status=ActionStatus.PROPOSED,
                dod=dod,
                result=result,
                validation=validation,
                transition=transition,
                plan=escalation_plan,
                revision_attempts=revision_attempts,
                revision_outcome=revision_outcome,
                warnings=warnings,
                reason=(
                    "DoD validation failed; revision strategy "
                    "escalate_to_human opened a plan-gate entry."
                ),
            )

        if revision_outcome == REVISION_OUTCOME_ROLLED_BACK:
            return ActionResult(
                status=ActionStatus.DENIED,
                dod=dod,
                result=result,
                validation=validation,
                transition=transition,
                revision_attempts=revision_attempts,
                revision_outcome=revision_outcome,
                warnings=warnings,
                reason=(
                    "DoD validation failed; revision strategy "
                    "rollback_and_log rolled the action back."
                ),
            )

        if revision_outcome == REVISION_OUTCOME_FAILED:
            return ActionResult(
                status=ActionStatus.NEEDS_CLARIFICATION,
                dod=dod,
                result=result,
                validation=validation,
                transition=transition,
                revision_attempts=revision_attempts,
                revision_outcome=revision_outcome,
                warnings=warnings,
                reason=(
                    "DoD re-derived during revision is incoherent "
                    "(clarification needed); rubric does not match "
                    "the request."
                ),
            )

        if non_autonomous_outcome == ON_FULFILLMENT_ABORT:
            return ActionResult(
                status=ActionStatus.DENIED,
                dod=dod,
                result=result,
                validation=validation,
                transition=transition,
                warnings=warnings,
                reason="DoD-Verfehlung mit on_fulfillment_failed=abort.",
            )

        return ActionResult(
            status=ActionStatus.APPLIED,
            dod=dod,
            result=result,
            validation=validation,
            transition=transition,
            revision_pending=revision_pending,
            revision_attempts=revision_attempts,
            revision_outcome=revision_outcome,
            warnings=warnings,
        )

    def _apply_fulfillment_policy(
        self,
        *,
        effector: Effector,
        kind: str,
        request: Any,
        ctx: dict[str, Any],
        dod: DoD,
        result: Any,
        validation: ValidationResult,
    ) -> tuple[Any, ValidationResult, str, list[str]]:
        """Handle DoD-fulfillment failure for non-AUTONOMOUS stages.

        Returns ``(result, validation, outcome, warnings)`` where
        ``outcome`` is one of ``""``, ``"warn"``, ``"retry"``,
        ``"abort"`` (matching ``on_fulfillment_failed`` setting names).
        """
        threshold = self.settings.fulfillment_score_pass
        mode = self.settings.on_fulfillment_failed
        unsatisfied_names = [r.name for r in validation.unsatisfied]
        warnings: list[str] = []

        if mode == ON_FULFILLMENT_RETRY:
            new_result = effector.act(request)
            new_validation = self.validator.validate(dod, new_result)
            if new_validation.is_fulfilled(threshold):
                return new_result, new_validation, ON_FULFILLMENT_RETRY, []
            warnings.append(
                "on_fulfillment_failed=retry: single retry exhausted; "
                f"unsatisfied: {', '.join(unsatisfied_names)}"
            )
            return new_result, new_validation, ON_FULFILLMENT_RETRY, warnings

        if mode == ON_FULFILLMENT_ABORT:
            self._invoke_rollback(
                effector=effector,
                kind=kind,
                request=request,
                result=result,
            )
            warnings.append(
                "on_fulfillment_failed=abort: action rolled back; "
                f"unsatisfied: {', '.join(unsatisfied_names)}"
            )
            return result, validation, ON_FULFILLMENT_ABORT, warnings

        # ON_FULFILLMENT_WARN (default)
        warnings.append(
            "on_fulfillment_failed=warn: unsatisfied: "
            + ", ".join(unsatisfied_names)
        )
        return result, validation, ON_FULFILLMENT_WARN, warnings

    def _run_revision_loop(
        self,
        *,
        effector: Effector,
        kind: str,
        request: Any,
        ctx: dict[str, Any],
        dod: DoD,
        result: Any,
        validation: ValidationResult,
    ) -> tuple[DoD, Any, ValidationResult, int, str, Any]:
        max_attempts = self.settings.autonomous_max_revision_attempts
        default_strategy = self.settings.default_revision_strategy
        revision_attempts = 0
        revision_outcome = REVISION_OUTCOME_NONE
        escalation_plan = None

        while not validation.all_satisfied:
            strategy = _decide_revision_strategy(
                validation.unsatisfied, default_strategy
            )

            if strategy == REVISION_ROLLBACK_AND_LOG:
                self._record_revision_lesson(
                    kind=kind,
                    validation=validation,
                    attempt=revision_attempts + 1,
                    context=ctx,
                )
                self._invoke_rollback(
                    effector=effector,
                    kind=kind,
                    request=request,
                    result=result,
                )
                revision_outcome = REVISION_OUTCOME_ROLLED_BACK
                break

            if strategy == REVISION_ESCALATE_TO_HUMAN:
                self._record_revision_lesson(
                    kind=kind,
                    validation=validation,
                    attempt=revision_attempts + 1,
                    context=ctx,
                )
                escalation_plan = self.plan_gate.propose(
                    kind=kind,
                    payload={
                        "request": request,
                        "context": dict(ctx),
                        "failed_criteria": [
                            r.name for r in validation.unsatisfied
                        ],
                    },
                    dod=dod,
                    proposed_by="orchestrator:revision_escalation",
                )
                revision_outcome = REVISION_OUTCOME_ESCALATED
                break

            # REVISION_RETRY_ALT_PARAMS — iterative retry up to max_attempts.
            if revision_attempts >= max_attempts:
                revision_outcome = REVISION_OUTCOME_EXHAUSTED
                break

            self._record_revision_lesson(
                kind=kind,
                validation=validation,
                attempt=revision_attempts + 1,
                context=ctx,
            )
            dod = self.engine.derive(request, ctx)
            if dod.clarification_needed:
                # DoD re-derivation surfaced a fresh clarification need —
                # the rubric is incoherent with the request. Mirrors
                # Anthropic Outcomes' `failed` result (distinct from
                # `max_iterations_reached`).
                revision_outcome = REVISION_OUTCOME_FAILED
                break
            result = effector.act(request)
            validation = self.validator.validate(dod, result)
            revision_attempts += 1

            if validation.all_satisfied:
                revision_outcome = REVISION_OUTCOME_COMPLETED
                break

        return (
            dod,
            result,
            validation,
            revision_attempts,
            revision_outcome,
            escalation_plan,
        )

    def _invoke_rollback(
        self,
        *,
        effector: Effector,
        kind: str,
        request: Any,
        result: Any,
    ) -> None:
        rollback = getattr(effector, "rollback", None)
        if not callable(rollback):
            return
        action_descriptor = {"kind": kind, "request": request}
        try:
            rollback(action_descriptor, result)
        except Exception as exc:
            if self.lessons_aggregator is None:
                return
            self.lessons_aggregator.record_lesson(
                kind=kind,
                observation=f"rollback failed: {exc}",
                criteria_hint=[],
                confidence_delta=0.0,
                context_pattern={},
                provenance=Provenance.now(
                    author="orchestrator",
                    source="rollback_failure",
                ),
            )

    def _record_revision_lesson(
        self,
        *,
        kind: str,
        validation,
        attempt: int,
        context: dict[str, Any],
    ) -> None:
        unsatisfied = list(validation.unsatisfied)
        unsatisfied_names = [r.name for r in unsatisfied]
        observation = (
            f"AUTONOMOUS revision attempt {attempt}: "
            f"validation failed on {len(unsatisfied_names)} criteria "
            f"({', '.join(unsatisfied_names)})"
        )
        weight_factor = self.settings.revision_lesson_weight_factor
        criteria_hint = [
            Criterion(
                name=r.name,
                expected=r.expected,
                weight=r.weight * weight_factor,
                source=REVISION_LESSON_SOURCE,
                evaluator=r.evaluator,
            )
            for r in unsatisfied
        ]
        context_pattern = {
            key: context[key]
            for key in self.settings.lesson_context_keys
            if key in context
        }
        self.lessons_aggregator.record_lesson(
            kind=kind,
            observation=observation,
            criteria_hint=criteria_hint,
            confidence_delta=0.0,
            context_pattern=context_pattern,
            provenance=Provenance.now(
                author="orchestrator",
                source=REVISION_LESSON_SOURCE,
            ),
        )

    def _record_trace(
        self,
        *,
        kind: str,
        request: Any,
        context: dict[str, Any],
        dod: DoD,
        stage: LifecycleStage,
        result: ActionResult,
        started_at: datetime,
        effector: Effector,
        proposed_by: str | None,
        source: str,
    ) -> str | None:
        if self.trace_store is None or not self.trace_settings.enabled:
            return None

        max_len = self.trace_settings.summary_max_length
        author = _proposed_by(effector, proposed_by)
        trace = Trace(
            id=str(uuid.uuid4()),
            kind=kind,
            request_summary=truncate_repr(request, max_len),
            context=dict(context),
            stage=stage,
            status=result.status,
            dod=dod,
            started_at=started_at,
            completed_at=_now(),
            provenance=Provenance.now(author=author, source=source),
            plan_id=result.plan.id if result.plan else None,
            result_summary=(
                truncate_repr(result.result, max_len)
                if result.result is not None
                else None
            ),
            validation=result.validation,
            transition_to=(
                result.transition.to_stage if result.transition else None
            ),
            revision_pending=result.revision_pending,
            reason=result.reason,
        )
        self.trace_store.write(trace)
        return trace.id

    def _publish_event(
        self, event_type: str, payload: dict[str, Any]
    ) -> None:
        if self.event_bus is None:
            return
        self.event_bus.publish(
            Event.now(
                type=event_type,
                payload=payload,
                provenance=Provenance.now(
                    author="orchestrator", source=event_type
                ),
            )
        )

    def _publish_transition_event(
        self, kind: str, result: ActionResult
    ) -> None:
        if result.transition is None:
            return
        self._publish_event(
            EVENT_LIFECYCLE_TRANSITION,
            {
                "kind": kind,
                "from_stage": result.transition.from_stage.value,
                "to_stage": result.transition.to_stage.value,
                "reason": result.transition.reason,
            },
        )


def _decide_revision_strategy(
    unsatisfied: list, default: str
) -> str:
    """Pick the strongest strategy demanded by any unsatisfied criterion.

    Each ``CriterionResult`` carries the ``revision_strategy`` from its
    originating ``Criterion`` (or ``None`` to fall back to the default).
    Severity ordering is fixed via ``REVISION_STRATEGY_PRIORITY``.
    """
    strategies = {
        (r.revision_strategy or default) for r in unsatisfied
    }
    for candidate in REVISION_STRATEGY_PRIORITY:
        if candidate in strategies:
            return candidate
    return default


def _proposed_by(effector: Any, override: str | None) -> str:
    if override:
        return override
    name = getattr(effector, "name", None)
    if isinstance(name, str) and name:
        return name
    return type(effector).__name__


def _now() -> datetime:
    return datetime.now(timezone.utc)
