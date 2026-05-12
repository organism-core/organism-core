"""Two-contact adapter for read-only tools.

Mirrors the 5-contact ``Effector`` Protocol but strips it down to
what a deterministic read actually needs:

    pre_load    context enrichment (user-scope, trace-id inheritance)
    query       the read itself — returns data, raises on error

Why not the other three:
- ``define_done`` is gone: deterministic reads have no acceptance
  criterion ("list of todos" is intrinsically defined). For
  probabilistic reads that DO need DoD-validation (OCR, vector-search-
  ranking, classification), use ``BaseEffector`` / ``ReadEffector``
  with ``ActionOrchestrator`` instead.
- ``upstream`` is gone: reads don't emit provenance or lessons. The
  ``QueryRunner`` writes a ``QueryTrace`` per call; that is the read-
  side observability.
- ``gate`` is gone: ACL is transport-middleware concern, not Querier
  responsibility.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Querier(Protocol):
    name: str

    def pre_load(self, context: dict[str, Any]) -> dict[str, Any]: ...

    def query(self, request: Any) -> Any: ...
