from __future__ import annotations

from typing import Any

from organism.query import BaseQuerier


class TaxReturnQuerier(BaseQuerier):
    """Synthetic read-only querier for the tax_lite demo.

    Looks up the latest tax return record for a client_id in a return_map.
    Deterministic, no side effects — fits the Querier path.
    """

    name = "tax_return_querier"

    def __init__(self, return_map: dict[str, Any]) -> None:
        self.return_map = dict(return_map)

    def query(self, request: Any) -> Any:
        if request not in self.return_map:
            raise KeyError(f"unknown client_id: {request!r}")
        return self.return_map[request]
