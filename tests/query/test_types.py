from __future__ import annotations

import pytest

from organism.query import QueryResult, QueryStatus


def test_query_status_string_enum():
    assert QueryStatus.OK.value == "ok"
    assert QueryStatus.ERROR.value == "error"


def test_query_result_defaults():
    r = QueryResult(status=QueryStatus.OK, kind="k", caller="c")
    assert r.result is None
    assert r.error == ""
    assert r.latency_ms == 0.0
    assert r.trace_id is None


def test_query_result_round_trip():
    original = QueryResult(
        status=QueryStatus.OK,
        kind="k",
        caller="c",
        result={"foo": 1},
        error="",
        latency_ms=12.5,
        trace_id="abc-123",
    )
    restored = QueryResult.from_dict(original.to_dict())
    assert restored == original


def test_query_result_error_round_trip():
    original = QueryResult(
        status=QueryStatus.ERROR,
        kind="k",
        caller="c",
        result=None,
        error="ValueError: boom",
        latency_ms=1.0,
    )
    restored = QueryResult.from_dict(original.to_dict())
    assert restored == original
    assert restored.status == QueryStatus.ERROR
