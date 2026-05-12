from __future__ import annotations

import pytest

from organism.observability import RegisteredTool, ToolRegistry


def test_register_returns_tool():
    registry = ToolRegistry()
    tool = registry.register(name="ef", kinds=["create", "update"])
    assert tool.name == "ef"
    assert tool.kinds == ["create", "update"]
    assert tool.description == ""


def test_register_with_description():
    registry = ToolRegistry()
    tool = registry.register(
        name="ef",
        kinds=["x"],
        description="Test effector for x-actions",
    )
    assert tool.description == "Test effector for x-actions"


def test_register_duplicate_name_raises():
    registry = ToolRegistry()
    registry.register(name="ef", kinds=["a"])
    with pytest.raises(ValueError, match="already registered"):
        registry.register(name="ef", kinds=["b"])


def test_get_returns_tool():
    registry = ToolRegistry()
    registry.register(name="ef", kinds=["a"])
    assert registry.get("ef").kinds == ["a"]


def test_get_unknown_raises():
    registry = ToolRegistry()
    with pytest.raises(KeyError, match="not registered"):
        registry.get("ghost")


def test_has():
    registry = ToolRegistry()
    assert not registry.has("ef")
    registry.register(name="ef", kinds=["a"])
    assert registry.has("ef")


def test_unregister_removes_tool():
    registry = ToolRegistry()
    registry.register(name="ef", kinds=["a"])
    registry.unregister("ef")
    assert not registry.has("ef")


def test_unregister_unknown_raises():
    registry = ToolRegistry()
    with pytest.raises(KeyError, match="not registered"):
        registry.unregister("ghost")


def test_list_returns_sorted():
    registry = ToolRegistry()
    registry.register(name="zeta", kinds=[])
    registry.register(name="alpha", kinds=[])
    registry.register(name="mike", kinds=[])
    assert [t.name for t in registry.list()] == ["alpha", "mike", "zeta"]


def test_find_for_kind_returns_matching_tools():
    registry = ToolRegistry()
    registry.register(name="ef_a", kinds=["create", "update"])
    registry.register(name="ef_b", kinds=["update", "delete"])
    registry.register(name="ef_c", kinds=["create"])

    matches = registry.find_for_kind("create")
    assert {t.name for t in matches} == {"ef_a", "ef_c"}

    matches_update = registry.find_for_kind("update")
    assert {t.name for t in matches_update} == {"ef_a", "ef_b"}


def test_find_for_kind_returns_empty_for_unknown():
    registry = ToolRegistry()
    registry.register(name="ef", kinds=["a"])
    assert registry.find_for_kind("ghost") == []


def test_registered_tool_round_trip():
    original = RegisteredTool(
        name="ef",
        kinds=["a", "b"],
        description="desc",
    )
    restored = RegisteredTool.from_dict(original.to_dict())
    assert restored == original


# tool_type field


def test_default_tool_type_is_empty():
    tool = RegisteredTool(name="x", kinds=["k"])
    assert tool.tool_type == ""


def test_to_dict_omits_default_tool_type():
    tool = RegisteredTool(name="x", kinds=["k"])
    assert "tool_type" not in tool.to_dict()


def test_to_dict_includes_non_default_tool_type():
    from organism.observability import TOOL_TYPE_QUERIER

    tool = RegisteredTool(name="x", kinds=["k"], tool_type=TOOL_TYPE_QUERIER)
    assert tool.to_dict()["tool_type"] == "querier"


def test_round_trip_preserves_tool_type():
    from organism.observability import TOOL_TYPE_EFFECTOR

    original = RegisteredTool(
        name="x", kinds=["k"], tool_type=TOOL_TYPE_EFFECTOR
    )
    restored = RegisteredTool.from_dict(original.to_dict())
    assert restored == original


def test_unknown_tool_type_rejected():
    with pytest.raises(ValueError, match="tool_type"):
        RegisteredTool(name="x", kinds=["k"], tool_type="invalid")


def test_register_accepts_tool_type_kwarg():
    from organism.observability import TOOL_TYPE_QUERIER

    registry = ToolRegistry()
    tool = registry.register(
        name="todo_q", kinds=["list"], tool_type=TOOL_TYPE_QUERIER
    )
    assert tool.tool_type == "querier"


def test_register_default_tool_type_is_empty():
    registry = ToolRegistry()
    tool = registry.register(name="ef", kinds=["k"])
    assert tool.tool_type == ""


def test_list_filters_by_tool_type():
    from organism.observability import (
        TOOL_TYPE_EFFECTOR,
        TOOL_TYPE_QUERIER,
    )

    registry = ToolRegistry()
    registry.register(name="ef_a", kinds=["k"], tool_type=TOOL_TYPE_EFFECTOR)
    registry.register(name="ef_b", kinds=["k"], tool_type=TOOL_TYPE_EFFECTOR)
    registry.register(name="q_a", kinds=["k"], tool_type=TOOL_TYPE_QUERIER)
    registry.register(name="legacy", kinds=["k"])  # tool_type=""

    queriers = registry.list(tool_type=TOOL_TYPE_QUERIER)
    assert [t.name for t in queriers] == ["q_a"]

    effectors = registry.list(tool_type=TOOL_TYPE_EFFECTOR)
    assert [t.name for t in effectors] == ["ef_a", "ef_b"]

    untyped = registry.list(tool_type="")
    assert [t.name for t in untyped] == ["legacy"]

    all_tools = registry.list()
    assert len(all_tools) == 4


def test_list_unknown_tool_type_filter_rejected():
    registry = ToolRegistry()
    with pytest.raises(ValueError, match="tool_type filter"):
        registry.list(tool_type="invalid")


def test_find_for_kind_filters_by_tool_type():
    from organism.observability import (
        TOOL_TYPE_EFFECTOR,
        TOOL_TYPE_QUERIER,
    )

    registry = ToolRegistry()
    registry.register(name="ef", kinds=["lookup"], tool_type=TOOL_TYPE_EFFECTOR)
    registry.register(name="q", kinds=["lookup"], tool_type=TOOL_TYPE_QUERIER)
    registry.register(name="untyped", kinds=["lookup"])

    queriers = registry.find_for_kind("lookup", tool_type=TOOL_TYPE_QUERIER)
    assert [t.name for t in queriers] == ["q"]

    effectors = registry.find_for_kind(
        "lookup", tool_type=TOOL_TYPE_EFFECTOR
    )
    assert [t.name for t in effectors] == ["ef"]

    all_matching = registry.find_for_kind("lookup")
    assert {t.name for t in all_matching} == {"ef", "q", "untyped"}
