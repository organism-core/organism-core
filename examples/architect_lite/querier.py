from __future__ import annotations

from typing import Any

from organism.query import BaseQuerier


class FloorPlanQuerier(BaseQuerier):
    """Synthetic read-only querier for the architect_lite demo.

    Looks up a cached extraction result by entity_id in a return_map and
    returns it. Deterministic, no side effects — fits the Querier path.
    """

    name = "floor_plan_querier"

    def __init__(self, return_map: dict[str, Any]) -> None:
        self.return_map = dict(return_map)

    def query(self, request: Any) -> Any:
        if request not in self.return_map:
            raise KeyError(f"unknown entity_id: {request!r}")
        return self.return_map[request]
