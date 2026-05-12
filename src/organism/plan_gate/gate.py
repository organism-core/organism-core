from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import datetime, timezone
from typing import Any

from organism.dod.types import DoD
from organism.plan_gate.settings import PlanGateSettings
from organism.plan_gate.store import PlanStore
from organism.plan_gate.types import Plan, PlanStatus


class PlanGate:
    def __init__(
        self,
        store: PlanStore,
        settings: PlanGateSettings | None = None,
    ) -> None:
        self.store = store
        self.settings = settings or PlanGateSettings()

    def propose(
        self,
        *,
        kind: str,
        payload: dict[str, Any],
        dod: DoD,
        proposed_by: str,
    ) -> Plan:
        plan = Plan(
            id=str(uuid.uuid4()),
            kind=kind,
            payload=dict(payload),
            dod=dod,
            status=PlanStatus.PROPOSED,
            proposed_by=proposed_by,
            proposed_at=_now(),
        )
        self.store.write(plan)
        return plan

    def approve(
        self, plan_id: str, *, decided_by: str, reason: str = ""
    ) -> Plan:
        self._require_reason_if_configured(reason)
        plan = self.store.read(plan_id)
        self._require_status(plan, PlanStatus.PROPOSED, "approve")
        approved = replace(
            plan,
            status=PlanStatus.APPROVED,
            decided_at=_now(),
            decided_by=decided_by,
            decision_reason=reason,
        )
        self.store.write(approved)
        return approved

    def reject(
        self, plan_id: str, *, decided_by: str, reason: str = ""
    ) -> Plan:
        self._require_reason_if_configured(reason)
        plan = self.store.read(plan_id)
        self._require_status(plan, PlanStatus.PROPOSED, "reject")
        rejected = replace(
            plan,
            status=PlanStatus.REJECTED,
            decided_at=_now(),
            decided_by=decided_by,
            decision_reason=reason,
        )
        self.store.write(rejected)
        return rejected

    def apply(self, plan_id: str) -> Plan:
        plan = self.store.read(plan_id)
        self._require_status(plan, PlanStatus.APPROVED, "apply")
        applied = replace(
            plan,
            status=PlanStatus.APPLIED,
            applied_at=_now(),
        )
        self.store.write(applied)
        return applied

    def get(self, plan_id: str) -> Plan:
        return self.store.read(plan_id)

    def list(
        self,
        kind: str | None = None,
        status: PlanStatus | None = None,
    ) -> list[Plan]:
        return self.store.list(kind=kind, status=status)

    def _require_status(
        self, plan: Plan, expected: PlanStatus, op: str
    ) -> None:
        if plan.status != expected:
            raise ValueError(
                f"Cannot {op} plan {plan.id!r}: status is "
                f"{plan.status.value!r}, expected {expected.value!r}"
            )

    def _require_reason_if_configured(self, reason: str) -> None:
        if self.settings.require_decision_reason and not reason:
            raise ValueError(
                "Decision reason is required (settings.require_decision_reason=True)"
            )


def _now() -> datetime:
    return datetime.now(timezone.utc)
