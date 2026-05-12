from __future__ import annotations

from typing import Any

import pytest

from organism.query import BaseQuerier, Querier


def test_base_satisfies_protocol():
    assert isinstance(BaseQuerier(), Querier)


def test_pre_load_passthrough():
    b = BaseQuerier()
    ctx = {"k": 1, "nested": {"x": 2}}
    assert b.pre_load(ctx) is ctx


def test_query_raises_by_default():
    with pytest.raises(NotImplementedError):
        BaseQuerier().query("anything")


class _TodoQuerier(BaseQuerier):
    name = "todo"

    def query(self, request: Any) -> Any:
        return {"todos": ["a", "b"]}


def test_subclass_only_needs_to_override_query():
    q = _TodoQuerier()
    assert isinstance(q, Querier)
    assert q.pre_load({"a": 1}) == {"a": 1}
    assert q.query("any") == {"todos": ["a", "b"]}
