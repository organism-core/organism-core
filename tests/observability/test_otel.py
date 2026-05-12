from __future__ import annotations

from datetime import datetime, timezone

from organism.dod import (
    Criterion,
    CriterionResult,
    DoD,
    ValidationResult,
)
from organism.lifecycle import LifecycleStage
from organism.observability import (
    OTEL_STATUS_ERROR,
    OTEL_STATUS_OK,
    OTEL_STATUS_UNSET,
    Trace,
    trace_to_otel_span,
)
from organism.orchestrator import ActionStatus
from organism.provenance import Provenance


def _make_trace(
    status: ActionStatus = ActionStatus.APPLIED,
    stage: LifecycleStage = LifecycleStage.CHECKED,
    validation: ValidationResult | None = None,
    plan_id: str | None = None,
    transition_to: LifecycleStage | None = None,
    revision_pending: bool = False,
    reason: str = "",
) -> Trace:
    return Trace(
        id="trace-001",
        kind="create_entity",
        request_summary="'hi'",
        context={},
        stage=stage,
        status=status,
        dod=DoD(
            criteria=[Criterion(name="x", expected=1)],
            confidence=0.85,
        ),
        started_at=datetime(2026, 5, 9, 10, 0, 0, tzinfo=timezone.utc),
        completed_at=datetime(2026, 5, 9, 10, 0, 1, tzinfo=timezone.utc),
        provenance=Provenance(
            author="ef",
            timestamp=datetime(2026, 5, 9, 10, 0, 1, tzinfo=timezone.utc),
            source="orchestrator.execute",
        ),
        plan_id=plan_id,
        validation=validation,
        transition_to=transition_to,
        revision_pending=revision_pending,
        reason=reason,
    )


def test_basic_attributes():
    span = trace_to_otel_span(_make_trace())
    attrs = span["attributes"]
    assert attrs["gen_ai.operation.name"] == "create_entity"
    assert attrs["gen_ai.system"] == "ef"
    assert attrs["organism.lifecycle.stage"] == "checked"
    assert attrs["organism.action.status"] == "applied"
    assert attrs["organism.dod.confidence"] == 0.85
    assert attrs["organism.dod.criteria_count"] == 1
    assert attrs["organism.revision_pending"] is False


def test_span_name_and_kind():
    span = trace_to_otel_span(_make_trace())
    assert span["name"] == "organism.execute.create_entity"
    assert span["kind"] == "INTERNAL"
    assert span["trace_id"] == "trace-001"


def test_timing_iso_strings():
    span = trace_to_otel_span(_make_trace())
    assert span["start_time"] == "2026-05-09T10:00:00+00:00"
    assert span["end_time"] == "2026-05-09T10:00:01+00:00"


def test_status_ok_for_applied_no_validation():
    span = trace_to_otel_span(_make_trace(status=ActionStatus.APPLIED))
    assert span["status"]["code"] == OTEL_STATUS_OK


def test_status_ok_for_applied_with_satisfied_validation():
    validation = ValidationResult(
        criterion_results=[
            CriterionResult(
                name="x",
                satisfied=True,
                weight=1.0,
                expected=1,
                actual=1,
            )
        ],
        score=1.0,
    )
    span = trace_to_otel_span(
        _make_trace(status=ActionStatus.APPLIED, validation=validation)
    )
    assert span["status"]["code"] == OTEL_STATUS_OK


def test_status_error_for_applied_with_unsatisfied_validation():
    validation = ValidationResult(
        criterion_results=[
            CriterionResult(
                name="x",
                satisfied=False,
                weight=1.0,
                expected=1,
                actual=2,
            )
        ],
        score=0.0,
    )
    span = trace_to_otel_span(
        _make_trace(status=ActionStatus.APPLIED, validation=validation)
    )
    assert span["status"]["code"] == OTEL_STATUS_ERROR


def test_status_error_for_denied():
    span = trace_to_otel_span(_make_trace(status=ActionStatus.DENIED))
    assert span["status"]["code"] == OTEL_STATUS_ERROR


def test_status_unset_for_proposed():
    span = trace_to_otel_span(_make_trace(status=ActionStatus.PROPOSED))
    assert span["status"]["code"] == OTEL_STATUS_UNSET


def test_status_unset_for_manual():
    span = trace_to_otel_span(_make_trace(status=ActionStatus.MANUAL))
    assert span["status"]["code"] == OTEL_STATUS_UNSET


def test_status_unset_for_needs_clarification():
    span = trace_to_otel_span(
        _make_trace(status=ActionStatus.NEEDS_CLARIFICATION)
    )
    assert span["status"]["code"] == OTEL_STATUS_UNSET


def test_plan_id_attribute_when_present():
    span = trace_to_otel_span(_make_trace(plan_id="plan-xyz"))
    assert span["attributes"]["organism.plan_id"] == "plan-xyz"


def test_plan_id_attribute_omitted_when_none():
    span = trace_to_otel_span(_make_trace(plan_id=None))
    assert "organism.plan_id" not in span["attributes"]


def test_validation_attributes_when_present():
    validation = ValidationResult(
        criterion_results=[
            CriterionResult(
                name="x",
                satisfied=True,
                weight=1.0,
                expected=1,
                actual=1,
            )
        ],
        score=1.0,
    )
    span = trace_to_otel_span(_make_trace(validation=validation))
    assert span["attributes"]["organism.validation.score"] == 1.0
    assert span["attributes"]["organism.validation.all_satisfied"] is True


def test_transition_attribute_when_present():
    span = trace_to_otel_span(
        _make_trace(transition_to=LifecycleStage.ROUTINE)
    )
    assert span["attributes"]["organism.transition.to_stage"] == "routine"


def test_reason_attribute_when_present():
    span = trace_to_otel_span(_make_trace(reason="some reason"))
    assert span["attributes"]["organism.reason"] == "some reason"


def test_reason_omitted_when_empty():
    span = trace_to_otel_span(_make_trace(reason=""))
    assert "organism.reason" not in span["attributes"]


def test_revision_pending_in_attributes():
    span = trace_to_otel_span(_make_trace(revision_pending=True))
    assert span["attributes"]["organism.revision_pending"] is True
