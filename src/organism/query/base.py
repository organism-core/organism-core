"""Default base class for the Querier contract.

Analogous to ``BaseEffector``: subclasses override only the contacts
they need. The main contact (``query``) raises by default — same
fail-loud principle as ``BaseEffector.act()`` — because no useful
no-op exists for "perform the read".
"""

from __future__ import annotations

from typing import Any


class BaseQuerier:
    name: str = ""

    def pre_load(self, context: dict[str, Any]) -> dict[str, Any]:
        return context

    def query(self, request: Any) -> Any:
        raise NotImplementedError(
            "Querier.query() must be implemented by subclass"
        )
