"""Vector-search source — wraps a duck-typed vector DB client (e.g.
chromadb) and contributes a generic ``similar_cases_present``
criterion plus confidence based on how many near-neighbours the
query found.

Skelett discipline:

- ``organism-core`` carries **no** vector-DB dependency. The
  ``client`` parameter is typed ``Any`` and the adapter only requires
  a chromadb-shaped ``query(query_texts=[...], n_results=N)`` method
  returning ``{"ids": [[...]], "distances": [[...]],
  "metadatas": [[...]]}``. Pinecone/Weaviate/Qdrant consumers ship
  their own thin adapter that exposes the same surface.
- Embedding choice belongs to the consumer, not the skelett. Whether
  the client uses sentence-transformers, OpenAI embeddings, or BM25
  is invisible here.
- V1 keeps the contribution schema flat: one
  ``similar_cases_present`` criterion when at least one hit comes
  back, plus a confidence_delta proportional to the hit count
  (capped). Aggregate statistics over hit metadata
  (e.g. "8 of 10 hits had status=done") are a future V2 once V1 is
  empirically validated.

The default ``query_builder`` is a generic stringifier prioritising
universal field names (``text``, ``description``, ``name``,
``title``, ``summary``) plus ``entity_id``/``kind`` from the request
context — fields that exist in any domain (architecture, tax,
finance, ...).
"""

from __future__ import annotations

from typing import Any, Callable

from organism.dod.settings import VectorSearchSettings
from organism.dod.types import Criterion, DoD, SourceContribution

QueryBuilder = Callable[[Any, dict[str, Any]], str]

SIMILAR_CASES_CRITERION = "similar_cases_present"
_REQUEST_TEXT_FIELDS: tuple[str, ...] = (
    "text",
    "description",
    "name",
    "title",
    "summary",
)
_CONTEXT_TEXT_FIELDS: tuple[str, ...] = ("entity_id", "kind")
_EMPTY_QUERY = "(empty query)"


def default_query_builder(
    request: Any, context: dict[str, Any]
) -> str:
    """Generic text-query builder.

    Strategy:
    - If ``request`` is a dict: prefer the first non-empty value
      among universal text fields (``text``/``description``/``name``/
      ``title``/``summary``); then append any remaining string fields
      as ``key: value``.
    - Otherwise: ``str(request)``.
    - Then append ``entity_id``/``kind`` from context as ``key:
      value``.
    Output uses ``|`` as separator to keep the result human-readable
    for debugging.
    """
    parts: list[str] = []

    if isinstance(request, dict):
        for key in _REQUEST_TEXT_FIELDS:
            v = request.get(key)
            if isinstance(v, str) and v:
                parts.append(v)
                break
        for k, v in request.items():
            if k == "op" or not isinstance(v, str) or not v:
                continue
            if k in _REQUEST_TEXT_FIELDS and v in parts:
                continue
            parts.append(f"{k}: {v}")
    else:
        parts.append(str(request))

    if isinstance(context, dict):
        for key in _CONTEXT_TEXT_FIELDS:
            v = context.get(key)
            if v:
                parts.append(f"{key}: {v}")

    return " | ".join(parts) or _EMPTY_QUERY


class VectorSearchSource:
    """Pulls a ``similar_cases_present`` signal from a vector DB."""

    name = "vector_search"

    def __init__(
        self,
        client: Any = None,
        *,
        settings: VectorSearchSettings | None = None,
        collection_name: str | None = None,
        query_builder: QueryBuilder | None = None,
    ) -> None:
        self.client = client
        self.settings = settings or VectorSearchSettings()
        self.collection_name = collection_name
        self.query_builder = query_builder or default_query_builder

    def contribute(
        self,
        request: Any,
        context: dict[str, Any],
        current: DoD,
    ) -> SourceContribution:
        if self.client is None:
            return SourceContribution(source_name=self.name)

        query_text = self.query_builder(request, context)
        try:
            hits = self._query(query_text)
        except Exception as exc:
            if not self.settings.fail_silently:
                raise
            return SourceContribution(
                source_name=self.name,
                evidence={
                    "error": f"{type(exc).__name__}: {str(exc)[:120]}",
                    "query": query_text,
                },
            )

        if not hits:
            return SourceContribution(
                source_name=self.name,
                evidence={"query": query_text, "results_count": 0},
            )

        # Skip if upstream already contributed similar_cases_present.
        if any(c.name == SIMILAR_CASES_CRITERION for c in current.criteria):
            criteria: list[Criterion] = []
        else:
            criteria = [
                Criterion(
                    name=SIMILAR_CASES_CRITERION,
                    expected=True,
                    weight=1.0,
                )
            ]

        delta = min(
            len(hits) * self.settings.confidence_per_result,
            self.settings.max_confidence_delta,
        )
        return SourceContribution(
            source_name=self.name,
            criteria=criteria,
            confidence_delta=delta,
            evidence={
                "query": query_text,
                "results_count": len(hits),
                "top_ids": [h["id"] for h in hits[:5]],
                "min_distance": min(
                    (h["distance"] for h in hits), default=None
                ),
            },
        )

    def _query(self, query_text: str) -> list[dict]:
        col = self.client
        if self.collection_name and hasattr(col, "get_collection"):
            col = col.get_collection(self.collection_name)

        raw = col.query(
            query_texts=[query_text],
            n_results=self.settings.n_results,
        )
        ids = (raw.get("ids") or [[]])[0]
        distances = (raw.get("distances") or [[]])[0]
        metadatas = (raw.get("metadatas") or [[]])[0]

        out: list[dict] = []
        for i, id_ in enumerate(ids):
            dist = distances[i] if i < len(distances) else 0.0
            if dist > self.settings.max_distance:
                continue
            meta = metadatas[i] if i < len(metadatas) else {}
            out.append({"id": id_, "distance": dist, "metadata": meta})
        return out
