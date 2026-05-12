from __future__ import annotations

from typing import Any

from organism.adapter import BaseEffector


class TaxReturnValidator(BaseEffector):
    """Synthetic effector for the tax_lite demo.

    Looks up the request (treated as client_id) in a return_map and
    returns the canned validation-result dict. Keeps the demo
    deterministic and doesn't pretend to do real tax-validation logic.

    Inherits from BaseEffector and overrides only the two contacts a
    typical effector cares about: ``define_done`` (returns empty so the
    DoD-Engine drives derivation) and ``act`` (the side-effect path).
    """

    name = "tax_return_validator"

    def __init__(self, return_map: dict[str, Any]) -> None:
        self.return_map = dict(return_map)

    def define_done(
        self, request: Any, context: dict[str, Any]
    ) -> dict[str, Any]:
        return {}

    def act(self, request: Any) -> Any:
        return self.return_map.get(request, {"all_income_recorded": False})
