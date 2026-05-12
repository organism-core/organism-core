from __future__ import annotations

from typing import Any

from organism.query import BaseQuerier


class CostCenterQuerier(BaseQuerier):
    """Synthetic read-only querier for the cfo_lite demo.

    Looks up a cost-center balance by period_id in a return_map.
    Deterministic, no side effects — fits the Querier path.
    """

    name = "cost_center_querier"

    def __init__(self, return_map: dict[str, Any]) -> None:
        self.return_map = dict(return_map)

    def query(self, request: Any) -> Any:
        if request not in self.return_map:
            raise KeyError(f"unknown period_id: {request!r}")
        return self.return_map[request]
