"""Five-contact adapter — minimum surface for a tool to plug into organism.

Patterns covered (cf. docs/ARCHITEKTUR/09_FRAMEWORK.md):
    pre_load     M1  — context lookup before action
    define_done  M5  — Definition-of-Done derivation
    act          --  — execute the action (lifecycle stage a-e)
    upstream     M2  — emit provenance / lesson / conflict
    gate         M3  — user-approval boundary

Concrete behavior is filled in later phases (DoD = 2, plan_gate = 3,
provenance/lessons = 4). This module defines the structural contract only.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Effector(Protocol):
    def pre_load(self, context: dict[str, Any]) -> dict[str, Any]: ...

    def define_done(
        self, request: Any, context: dict[str, Any]
    ) -> dict[str, Any]: ...

    def act(self, request: Any) -> Any: ...

    def upstream(self, kind: str, payload: dict[str, Any]) -> None: ...

    def gate(self, action: dict[str, Any]) -> bool: ...
