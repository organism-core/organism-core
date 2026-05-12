"""Default base classes for the Effector contract.

``BaseEffector`` is the side-effect-capable default. Tools subclass it
and override only the contacts they need:

    pre_load       passthrough  — return context unchanged
    define_done    blocks act() — non-empty clarification_needed forces
                                  the subclass to define DoD before acting
    act            raises       — no sensible no-op for the side-effect path
    upstream       silent       — Phase 4 will wire to provenance/lessons
    gate           allows       — read-only default; subclasses with
                                  side-effects override to delegate to
                                  plan_gate (Phase 3)

``ReadEffector`` is the read-only variant. Same shape, but with defaults
tuned for deterministic lookups (file reads, DB queries, exact schema
matches — the cases the M5 patch calls out as "DoD-Recherche verzichtbar").
It overrides two defaults:

    define_done    returns empty — reads don't need a safety-gate via DoD
    read_only      class attribute, True — introspection marker

``act`` still raises in ReadEffector: there is no useful default return
value for "perform the read", so subclasses must implement it explicitly
(fail-loud over silent-no-op).
"""

from __future__ import annotations

from typing import Any


class BaseEffector:
    read_only: bool = False

    def pre_load(self, context: dict[str, Any]) -> dict[str, Any]:
        return context

    def define_done(
        self, request: Any, context: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "criteria": [],
            "clarification_needed": [
                "DoD not defined for this effector — override define_done()"
            ],
            "confidence": 0.0,
        }

    def act(self, request: Any) -> Any:
        raise NotImplementedError(
            "Effector.act() must be implemented by subclass"
        )

    def upstream(self, kind: str, payload: dict[str, Any]) -> None:
        return None

    def gate(self, action: dict[str, Any]) -> bool:
        return True


class ReadEffector(BaseEffector):
    """Niche base class for **probabilistic** read-only effectors.

    Use this when a read needs DoD-validation — typical cases:
    OCR / classification / vector-search-ranking / plan-recognition.
    The result is data, not a side effect, but it can be wrong (the
    OCR returns 27 rooms instead of 30), so the M5 acceptance-criterion
    machinery applies. ``ActionOrchestrator`` is the right runner, and
    the consumer wires a DoD via the engine.

    For **deterministic** reads (SQL lookups, file reads, todo lists,
    exact schema matches) use ``organism.query.BaseQuerier`` instead —
    that's a simpler 2-method protocol with a dedicated ``QueryRunner``
    that skips DoD / plan-gate / lifecycle ceremony.

    Defaults compared to BaseEffector:
    - ``define_done`` returns empty dict (no clarification blocker) so
      the engine-derived DoD is the only acceptance source.
    - ``gate`` allows by default — reads don't need human approval.
    - ``read_only = True`` as introspection marker.

    ``act`` still raises ``NotImplementedError`` until the subclass
    implements the read logic — same fail-loud principle as BaseEffector.
    """

    read_only: bool = True

    def define_done(
        self, request: Any, context: dict[str, Any]
    ) -> dict[str, Any]:
        return {}

    def gate(self, action: dict[str, Any]) -> bool:
        return True
