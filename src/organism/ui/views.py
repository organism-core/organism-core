"""Render schemas — typed dataclasses for headless UI generators.

Each view is a pure data shape with ``to_dict()`` for serialization and
classmethod constructors that map from the corresponding domain object
(``DoD``, ``Plan``, ``LifecycleState``). UI consumers — React, Vue,
terminal-TUI, IDE plugin, Slack bot — render however they like; the
Skelett owns the data, not the presentation.

The views are intentionally *flat* (no nested objects beyond what's
strictly needed) so that a JSON-RPC bridge or template engine can pick
them up without further mapping.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from organism.dod.types import (
    EVALUATOR_LLM_JUDGE,
    EVALUATOR_RULE,
    EVALUATOR_SELF_CHECK,
    Criterion,
    DoD,
)
from organism.lifecycle.settings import LifecycleSettings
from organism.lifecycle.types import (
    STAGE_ORDER,
    ActionOutcome,
    LifecycleStage,
    LifecycleState,
    stage_above,
    stage_below,
)
from organism.plan_gate.types import Plan, PlanStatus


# ---------- Action descriptors for plan-approval UIs


@dataclass
class ApprovalAction:
    """Describes one button / menu-entry the UI should expose for a
    pending plan. Richer than a plain "approve / reject" pair so that
    UIs can render confirmation prompts, severity colors, and reason-
    fields without baking those decisions into the frontend."""

    id: str                          # "approve" | "reject" | ...
    label: str                       # human-friendly button text
    severity: str                    # "primary" | "danger" | "secondary"
    requires_confirmation: bool      # show a "are you sure?" gate
    requires_reason: bool            # require a free-text reason
    confirmation_prompt: str         # body of the confirmation dialog
    available: bool = True           # False = render disabled

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_APPROVE = ApprovalAction(
    id="approve",
    label="Approve & apply",
    severity="primary",
    requires_confirmation=True,
    requires_reason=False,
    confirmation_prompt=(
        "Approving will trigger effector.act() with this DoD as the "
        "validation gate. Continue?"
    ),
)
_REJECT = ApprovalAction(
    id="reject",
    label="Reject",
    severity="danger",
    requires_confirmation=False,
    requires_reason=True,
    confirmation_prompt=(
        "Rejecting will close this plan without execution. The reason "
        "field is required."
    ),
)


# ---------- Criterion + DoD views


@dataclass
class CriterionView:
    name: str
    expected_display: str            # human-readable repr of expected
    weight: float
    evaluator: str
    revision_strategy: str | None
    source: str
    is_qualitative: bool             # evaluator != rule

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_criterion(cls, c: Criterion) -> CriterionView:
        return cls(
            name=c.name,
            expected_display=_short_repr(c.expected, 60),
            weight=c.weight,
            evaluator=c.evaluator,
            revision_strategy=c.revision_strategy,
            source=c.source,
            is_qualitative=c.evaluator != EVALUATOR_RULE,
        )


@dataclass
class DoDView:
    criteria: list[CriterionView]
    total_weight: float
    confidence: float
    clarification_needed: list[str]
    evidence_sources: list[str]
    provenance_summary: dict[str, int]
    evaluator_breakdown: dict[str, int]
    qualitative_count: int
    revision_strategy_summary: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "criteria": [c.to_dict() for c in self.criteria],
            "total_weight": self.total_weight,
            "confidence": self.confidence,
            "clarification_needed": list(self.clarification_needed),
            "evidence_sources": list(self.evidence_sources),
            "provenance_summary": dict(self.provenance_summary),
            "evaluator_breakdown": dict(self.evaluator_breakdown),
            "qualitative_count": self.qualitative_count,
            "revision_strategy_summary": dict(self.revision_strategy_summary),
        }

    @classmethod
    def from_dod(cls, dod: DoD) -> DoDView:
        criteria = sorted(
            [CriterionView.from_criterion(c) for c in dod.criteria],
            key=lambda cv: cv.weight,
            reverse=True,
        )
        total_weight = sum(c.weight for c in dod.criteria)

        provenance: dict[str, int] = {}
        for source, names in dod._provenance.items():
            provenance[source] = len(names)

        evaluator_breakdown = {
            EVALUATOR_RULE: 0,
            EVALUATOR_SELF_CHECK: 0,
            EVALUATOR_LLM_JUDGE: 0,
        }
        for c in dod.criteria:
            evaluator_breakdown[c.evaluator] = (
                evaluator_breakdown.get(c.evaluator, 0) + 1
            )
        qualitative = sum(
            1 for c in dod.criteria if c.evaluator != EVALUATOR_RULE
        )

        strategy_summary: dict[str, int] = {}
        for c in dod.criteria:
            if c.revision_strategy is None:
                continue
            strategy_summary[c.revision_strategy] = (
                strategy_summary.get(c.revision_strategy, 0) + 1
            )

        return cls(
            criteria=criteria,
            total_weight=total_weight,
            confidence=dod.confidence,
            clarification_needed=list(dod.clarification_needed),
            evidence_sources=list(dod.evidence_sources),
            provenance_summary=provenance,
            evaluator_breakdown=evaluator_breakdown,
            qualitative_count=qualitative,
            revision_strategy_summary=strategy_summary,
        )


# ---------- Plan approval view


@dataclass
class PlanApprovalView:
    plan_id: str
    kind: str
    status: str
    proposed_by: str
    proposed_at: str
    decided_by: str | None
    decided_at: str | None
    applied_at: str | None
    decision_reason: str
    dod: DoDView
    request_summary: str
    payload_summary: dict[str, str]
    actions_available: list[ApprovalAction]
    is_revision_escalation: bool
    failed_criteria: list[str]
    age_seconds: float | None        # None if status != PROPOSED
    diff_hints: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "kind": self.kind,
            "status": self.status,
            "proposed_by": self.proposed_by,
            "proposed_at": self.proposed_at,
            "decided_by": self.decided_by,
            "decided_at": self.decided_at,
            "applied_at": self.applied_at,
            "decision_reason": self.decision_reason,
            "dod": self.dod.to_dict(),
            "request_summary": self.request_summary,
            "payload_summary": dict(self.payload_summary),
            "actions_available": [
                a.to_dict() for a in self.actions_available
            ],
            "is_revision_escalation": self.is_revision_escalation,
            "failed_criteria": list(self.failed_criteria),
            "age_seconds": self.age_seconds,
            "diff_hints": list(self.diff_hints),
        }

    @classmethod
    def from_plan(
        cls,
        plan: Plan,
        *,
        payload_repr_max_length: int,
        now_iso: str | None = None,
        diff_hints: list[str] | None = None,
    ) -> PlanApprovalView:
        from datetime import datetime, timezone

        request = plan.payload.get("request")
        request_summary = _short_repr(request, payload_repr_max_length)

        payload_summary: dict[str, str] = {}
        for key, value in plan.payload.items():
            if key == "request":
                continue
            payload_summary[str(key)] = _short_repr(
                value, payload_repr_max_length
            )

        is_revision = plan.proposed_by == "orchestrator:revision_escalation"
        failed_criteria = list(plan.payload.get("failed_criteria") or [])

        # Action availability is status-driven.
        actions: list[ApprovalAction] = []
        if plan.status == PlanStatus.PROPOSED:
            actions = [_APPROVE, _REJECT]
        # For any other status (APPROVED/REJECTED/APPLIED/EXPIRED) we
        # expose no actions — the plan is closed for human input.

        age = None
        if plan.status == PlanStatus.PROPOSED:
            now = (
                datetime.fromisoformat(now_iso)
                if now_iso
                else datetime.now(timezone.utc)
            )
            age = (now - plan.proposed_at).total_seconds()

        return cls(
            plan_id=plan.id,
            kind=plan.kind,
            status=plan.status.value,
            proposed_by=plan.proposed_by,
            proposed_at=plan.proposed_at.isoformat(),
            decided_by=plan.decided_by,
            decided_at=(
                plan.decided_at.isoformat() if plan.decided_at else None
            ),
            applied_at=(
                plan.applied_at.isoformat() if plan.applied_at else None
            ),
            decision_reason=plan.decision_reason,
            dod=DoDView.from_dod(plan.dod),
            request_summary=request_summary,
            payload_summary=payload_summary,
            actions_available=actions,
            is_revision_escalation=is_revision,
            failed_criteria=failed_criteria,
            age_seconds=age,
            diff_hints=list(diff_hints or []),
        )


# ---------- Drift view


@dataclass
class DriftView:
    kind: str
    current_stage: str
    current_stage_index: int
    outcomes_count: int
    recent_scores: list[float]
    avg_score: float
    score_trend: str                  # improving | stable | degrading | unknown
    promote_score_threshold: float
    demote_score_threshold: float
    promote_after_n: int
    demote_after_n: int
    distance_to_promote: float        # avg - promote_threshold
    distance_to_demote: float         # avg - demote_threshold
    drift_warning: bool
    stage_above: str | None
    stage_below: str | None
    last_transition: dict[str, Any] | None
    transition_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "current_stage": self.current_stage,
            "current_stage_index": self.current_stage_index,
            "outcomes_count": self.outcomes_count,
            "recent_scores": list(self.recent_scores),
            "avg_score": self.avg_score,
            "score_trend": self.score_trend,
            "promote_score_threshold": self.promote_score_threshold,
            "demote_score_threshold": self.demote_score_threshold,
            "promote_after_n": self.promote_after_n,
            "demote_after_n": self.demote_after_n,
            "distance_to_promote": self.distance_to_promote,
            "distance_to_demote": self.distance_to_demote,
            "drift_warning": self.drift_warning,
            "stage_above": self.stage_above,
            "stage_below": self.stage_below,
            "last_transition": (
                dict(self.last_transition) if self.last_transition else None
            ),
            "transition_count": self.transition_count,
        }

    @classmethod
    def from_state(
        cls,
        state: LifecycleState,
        settings: LifecycleSettings,
        *,
        trend_window: int,
        drift_warning_band: float,
    ) -> DriftView:
        outcomes = list(state.recent_outcomes)
        scores = [o.score for o in outcomes]
        recent = scores[-trend_window:]
        avg = sum(recent) / len(recent) if recent else 0.0
        trend = _trend_bucket(recent)

        distance_to_promote = avg - settings.promote_score_threshold
        distance_to_demote = avg - settings.demote_score_threshold

        # Fire only when there is enough data for the demote
        # evaluation; covers both "approaching" (distance within
        # configured band above zero) and "already below" (negative).
        # Tiny epsilon absorbs float-arithmetic quirks at the boundary.
        drift_warning = (
            len(outcomes) >= settings.demote_after_n
            and distance_to_demote <= drift_warning_band + 1e-9
        )

        above = stage_above(state.stage)
        below = stage_below(state.stage)

        last_transition = None
        if state.transition_history:
            last = state.transition_history[-1]
            last_transition = last.to_dict()

        return cls(
            kind=state.kind,
            current_stage=state.stage.value,
            current_stage_index=STAGE_ORDER.index(state.stage),
            outcomes_count=len(outcomes),
            recent_scores=recent,
            avg_score=avg,
            score_trend=trend,
            promote_score_threshold=settings.promote_score_threshold,
            demote_score_threshold=settings.demote_score_threshold,
            promote_after_n=settings.promote_after_n,
            demote_after_n=settings.demote_after_n,
            distance_to_promote=distance_to_promote,
            distance_to_demote=distance_to_demote,
            drift_warning=drift_warning,
            stage_above=above.value if above else None,
            stage_below=below.value if below else None,
            last_transition=last_transition,
            transition_count=len(state.transition_history),
        )


# ---------- Effector summary view


@dataclass
class EffectorSummaryView:
    """High-level row per ``kind`` for dashboard listings.

    The trailing ``lessons_age_days_p95`` + ``lessons_recent_use_ratio``
    + ``lessons_never_used_count`` fields are the lesson-pile
    observability sensor: watch ``lessons_count`` rising while
    ``lessons_age_days_p95`` rises and ``lessons_recent_use_ratio``
    falls — the signal that lessons are piling up without being picked
    up by queries (the failure mode a future distillation worker would
    address).
    """

    kind: str
    current_stage: str
    avg_score: float
    outcomes_count: int
    pending_plans: int
    lessons_count: int
    drift_warning: bool
    lessons_age_days_p95: float | None = None
    lessons_recent_use_ratio: float = 0.0
    lessons_never_used_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------- Query trace view (read-only path)


@dataclass
class QueryTraceView:
    """Render schema for a single QueryTrace — used by Cockpit.recent_queries().

    Mirrors the QueryTrace's flat shape but with summarized request /
    result fields and an ISO-formatted timestamp string so UIs can
    render the row without parsing datetimes themselves.
    """

    trace_id: str
    kind: str
    timestamp: str
    caller: str
    request_summary: str
    result_summary: str
    latency_ms: float
    status: str
    error: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_trace(cls, trace: Any) -> QueryTraceView:
        return cls(
            trace_id=trace.id,
            kind=trace.kind,
            timestamp=trace.timestamp.isoformat(),
            caller=trace.caller,
            request_summary=trace.request_repr,
            result_summary=trace.result_repr,
            latency_ms=trace.latency_ms,
            status=trace.status.value,
            error=trace.error,
        )


# ---------- helpers


def _short_repr(value: Any, max_length: int) -> str:
    text = repr(value)
    if len(text) <= max_length:
        return text
    return text[: max_length - 1] + "…"


def _trend_bucket(scores: list[float]) -> str:
    if len(scores) < 2:
        return "unknown"
    mid = len(scores) // 2
    first_half = scores[:mid] or scores[:1]
    second_half = scores[mid:] or scores[-1:]
    first_avg = sum(first_half) / len(first_half)
    second_avg = sum(second_half) / len(second_half)
    delta = second_avg - first_avg
    if delta > 0.05:
        return "improving"
    if delta < -0.05:
        return "degrading"
    return "stable"
