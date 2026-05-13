"""Tests for ``VectorSearchSource`` and ``default_query_builder``.

The source is verified against a duck-typed fake client — no
chromadb (or any other vector DB) dependency in the test suite.
"""

from __future__ import annotations

from typing import Any

import pytest

from organism.dod import (
    DoD,
    DoDEngine,
    DoDEngineSettings,
    VectorSearchSettings,
    VectorSearchSource,
    SourceContribution,
)
from organism.dod.sources.vector_search import (
    SIMILAR_CASES_CRITERION,
    default_query_builder,
)


# ============================================================
# Fake chromadb-shaped client
# ============================================================


class FakeChromaClient:
    """Minimal chromadb-shaped duck. ``query()`` returns the
    pre-canned ``response`` payload."""

    def __init__(self, response: dict[str, Any] | None = None):
        self.response = response or {
            "ids": [[]],
            "distances": [[]],
            "metadatas": [[]],
        }
        self.calls: list[dict[str, Any]] = []

    def query(self, *, query_texts: list[str], n_results: int):
        self.calls.append(
            {"query_texts": query_texts, "n_results": n_results}
        )
        return self.response


class FakeCollectionAwareClient:
    """Mimics chromadb's ``Client.get_collection`` indirection."""

    def __init__(self, collections: dict[str, FakeChromaClient]):
        self.collections = collections
        self.get_collection_calls: list[str] = []

    def get_collection(self, name: str) -> FakeChromaClient:
        self.get_collection_calls.append(name)
        return self.collections[name]


# ============================================================
# default_query_builder
# ============================================================


def test_query_builder_string_request_passthrough():
    out = default_query_builder("review the spec", {})
    assert out == "review the spec"


def test_query_builder_prefers_description_field():
    out = default_query_builder(
        {"description": "Jahresabschluss-Erstellung", "op": "act"},
        {},
    )
    assert "Jahresabschluss-Erstellung" in out


def test_query_builder_priority_order_text_first():
    out = default_query_builder(
        {
            "text": "primary",
            "description": "secondary",
            "name": "tertiary",
        },
        {},
    )
    # 'primary' first because text wins
    assert out.startswith("primary")


def test_query_builder_appends_other_string_fields():
    out = default_query_builder(
        {"text": "core", "category": "alpha"},
        {},
    )
    assert "core" in out
    assert "category: alpha" in out


def test_query_builder_skips_op_field():
    out = default_query_builder(
        {"text": "hi", "op": "act"},
        {},
    )
    assert "op:" not in out


def test_query_builder_appends_entity_id_and_kind_from_context():
    out = default_query_builder(
        "core query",
        {"entity_id": "alpha", "kind": "review"},
    )
    assert "entity_id: alpha" in out
    assert "kind: review" in out


def test_query_builder_separator_is_pipe():
    out = default_query_builder(
        {"text": "a", "category": "b"},
        {"entity_id": "alpha"},
    )
    # contains pipe separators between parts
    assert " | " in out


def test_query_builder_empty_request_falls_back_to_marker():
    out = default_query_builder({}, {})
    assert out == "(empty query)"


def test_query_builder_skips_empty_strings():
    out = default_query_builder(
        {"text": "", "description": "real"},
        {},
    )
    assert "real" in out


def test_query_builder_skips_non_string_request_fields():
    out = default_query_builder(
        {"text": "core", "count": 42, "flag": True},
        {},
    )
    assert "core" in out
    assert "count" not in out
    assert "flag" not in out


# ============================================================
# Source — no client (stub)
# ============================================================


def test_no_client_returns_empty():
    src = VectorSearchSource()
    out = src.contribute(request="r", context={}, current=DoD())
    assert out.criteria == []
    assert out.evidence == {}
    assert out.confidence_delta == 0.0


# ============================================================
# Source — hits
# ============================================================


def test_hits_emit_similar_cases_criterion():
    client = FakeChromaClient(
        response={
            "ids": [["a", "b", "c"]],
            "distances": [[0.1, 0.2, 0.3]],
            "metadatas": [[{}, {}, {}]],
        }
    )
    src = VectorSearchSource(client=client)
    out = src.contribute(request="r", context={}, current=DoD())
    assert [c.name for c in out.criteria] == [SIMILAR_CASES_CRITERION]
    assert out.evidence["results_count"] == 3
    assert out.evidence["top_ids"] == ["a", "b", "c"]
    assert out.evidence["min_distance"] == pytest.approx(0.1)


def test_no_hits_records_zero_count():
    client = FakeChromaClient()  # empty response
    src = VectorSearchSource(client=client)
    out = src.contribute(request="r", context={}, current=DoD())
    assert out.criteria == []
    assert out.evidence["results_count"] == 0


def test_confidence_scales_with_hit_count():
    client = FakeChromaClient(
        response={
            "ids": [["a", "b", "c", "d"]],
            "distances": [[0.1, 0.2, 0.3, 0.4]],
            "metadatas": [[{}, {}, {}, {}]],
        }
    )
    src = VectorSearchSource(
        client=client,
        settings=VectorSearchSettings(
            confidence_per_result=0.1, max_confidence_delta=1.0
        ),
    )
    out = src.contribute(request="r", context={}, current=DoD())
    assert out.confidence_delta == pytest.approx(0.4)


def test_confidence_capped_at_max_delta():
    client = FakeChromaClient(
        response={
            "ids": [[f"id_{i}" for i in range(50)]],
            "distances": [[0.1] * 50],
            "metadatas": [[{}] * 50],
        }
    )
    src = VectorSearchSource(
        client=client,
        settings=VectorSearchSettings(
            confidence_per_result=0.1, max_confidence_delta=0.5
        ),
    )
    out = src.contribute(request="r", context={}, current=DoD())
    assert out.confidence_delta == 0.5  # capped, not 5.0


# ============================================================
# Source — max_distance filter
# ============================================================


def test_drops_hits_above_max_distance():
    client = FakeChromaClient(
        response={
            "ids": [["near", "far"]],
            "distances": [[0.2, 2.0]],
            "metadatas": [[{}, {}]],
        }
    )
    src = VectorSearchSource(
        client=client,
        settings=VectorSearchSettings(max_distance=1.0),
    )
    out = src.contribute(request="r", context={}, current=DoD())
    assert out.evidence["results_count"] == 1
    assert out.evidence["top_ids"] == ["near"]


# ============================================================
# Source — error handling
# ============================================================


class _BoomClient:
    def query(self, **kwargs):
        raise RuntimeError("vector db down")


def test_fail_silently_captures_error_in_evidence():
    src = VectorSearchSource(
        client=_BoomClient(),
        settings=VectorSearchSettings(fail_silently=True),
    )
    out = src.contribute(request="r", context={}, current=DoD())
    assert out.criteria == []
    assert "error" in out.evidence
    assert "vector db down" in out.evidence["error"]


def test_fail_loudly_raises():
    src = VectorSearchSource(
        client=_BoomClient(),
        settings=VectorSearchSettings(fail_silently=False),
    )
    with pytest.raises(RuntimeError, match="vector db down"):
        src.contribute(request="r", context={}, current=DoD())


# ============================================================
# Source — collection routing
# ============================================================


def test_collection_name_routes_via_get_collection():
    target = FakeChromaClient(
        response={
            "ids": [["x"]],
            "distances": [[0.1]],
            "metadatas": [[{}]],
        }
    )
    container = FakeCollectionAwareClient({"focused": target})
    src = VectorSearchSource(
        client=container, collection_name="focused"
    )
    out = src.contribute(request="r", context={}, current=DoD())
    assert container.get_collection_calls == ["focused"]
    assert target.calls and target.calls[0]["query_texts"]
    assert out.evidence["results_count"] == 1


def test_no_collection_name_uses_client_directly():
    client = FakeChromaClient(
        response={
            "ids": [["x"]],
            "distances": [[0.1]],
            "metadatas": [[{}]],
        }
    )
    src = VectorSearchSource(client=client)  # no collection
    src.contribute(request="r", context={}, current=DoD())
    assert len(client.calls) == 1


# ============================================================
# Source — query_builder integration
# ============================================================


def test_default_query_builder_is_used():
    client = FakeChromaClient()
    src = VectorSearchSource(client=client)
    src.contribute(
        request={"description": "Jahresabschluss"},
        context={"entity_id": "mandant_42", "kind": "review"},
        current=DoD(),
    )
    [call] = client.calls
    sent = call["query_texts"][0]
    assert "Jahresabschluss" in sent
    assert "entity_id: mandant_42" in sent
    assert "kind: review" in sent


def test_custom_query_builder_is_called():
    seen: dict = {}

    def my_builder(request, context):
        seen["request"] = request
        seen["context"] = context
        return "FIXED_QUERY"

    client = FakeChromaClient()
    src = VectorSearchSource(client=client, query_builder=my_builder)
    src.contribute(
        request={"x": 1}, context={"y": 2}, current=DoD()
    )
    assert seen["request"] == {"x": 1}
    assert seen["context"] == {"y": 2}
    assert client.calls[0]["query_texts"] == ["FIXED_QUERY"]


def test_n_results_passed_through_to_client():
    client = FakeChromaClient()
    src = VectorSearchSource(
        client=client,
        settings=VectorSearchSettings(n_results=42),
    )
    src.contribute(request="r", context={}, current=DoD())
    assert client.calls[0]["n_results"] == 42


# ============================================================
# Source — dedup against current
# ============================================================


def test_skips_criterion_if_already_in_current():
    from organism.dod.types import Criterion

    client = FakeChromaClient(
        response={
            "ids": [["a"]],
            "distances": [[0.1]],
            "metadatas": [[{}]],
        }
    )
    src = VectorSearchSource(client=client)
    current = DoD(
        criteria=[Criterion(name=SIMILAR_CASES_CRITERION, expected=True)]
    )
    out = src.contribute(request="r", context={}, current=current)
    # No new criterion added — but confidence still increments.
    assert out.criteria == []
    assert out.confidence_delta > 0.0


# ============================================================
# Engine integration
# ============================================================


def test_engine_uses_vector_search_source():
    client = FakeChromaClient(
        response={
            "ids": [["a", "b"]],
            "distances": [[0.1, 0.2]],
            "metadatas": [[{}, {}]],
        }
    )
    engine = DoDEngine(
        sources=[VectorSearchSource(client=client)],
        settings=DoDEngineSettings(threshold=1.0),
    )
    dod = engine.derive(request="r", context={})
    assert "vector_search" in dod._provenance
    assert dod._provenance["vector_search"] == [SIMILAR_CASES_CRITERION]


# ============================================================
# Settings validation
# ============================================================


def test_settings_validation_rejects_invalid_n_results():
    with pytest.raises(ValueError):
        VectorSearchSettings(n_results=0)


def test_settings_validation_rejects_negative_distance():
    with pytest.raises(ValueError):
        VectorSearchSettings(max_distance=-1.0)


def test_settings_validation_rejects_oob_confidence():
    with pytest.raises(ValueError):
        VectorSearchSettings(confidence_per_result=1.5)
