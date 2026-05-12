from __future__ import annotations

from typing import Any

from organism.adapter import BaseEffector


class QuarterlyCloseRunner(BaseEffector):
    """Synthetic effector for the cfo_lite demo.

    Looks up the request (treated as period_id) in a return_map and
    returns the canned close-result dict. Keeps the demo deterministic
    and doesn't pretend to do real period-close logic.

    Inherits from BaseEffector and overrides only the two contacts a
    typical effector cares about: ``define_done`` (returns empty so the
    DoD-Engine drives derivation) and ``act`` (the side-effect path).
    """

    name = "quarterly_close_runner"

    def __init__(self, return_map: dict[str, Any]) -> None:
        self.return_map = dict(return_map)

    def define_done(
        self, request: Any, context: dict[str, Any]
    ) -> dict[str, Any]:
        return {}

    def act(self, request: Any) -> Any:
        return self.return_map.get(request, {"cost_centers_closed": False})
