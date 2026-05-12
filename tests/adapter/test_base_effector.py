from typing import Any

import pytest

from organism.adapter import BaseEffector, Effector


def test_base_satisfies_protocol():
    assert isinstance(BaseEffector(), Effector)


def test_pre_load_returns_same_context_object():
    base = BaseEffector()
    ctx = {"k": 1, "nested": {"x": 2}}
    assert base.pre_load(ctx) is ctx


def test_define_done_default_blocks_act_via_clarification():
    dod = BaseEffector().define_done("any-request", {})
    assert dod["criteria"] == []
    assert dod["clarification_needed"]
    assert dod["confidence"] == 0.0


def test_act_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        BaseEffector().act("anything")


def test_upstream_default_is_silent_no_op():
    assert BaseEffector().upstream("lesson", {"x": 1}) is None


def test_gate_default_allows():
    assert BaseEffector().gate({"kind": "write"}) is True


class _PartialOverrideTool(BaseEffector):
    def define_done(
        self, request: Any, context: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "criteria": [{"name": "result_is_positive"}],
            "clarification_needed": [],
            "confidence": 0.9,
        }

    def act(self, request: Any) -> Any:
        return {"result": request * 2}


def test_subclass_overriding_only_required_methods():
    tool = _PartialOverrideTool()
    assert isinstance(tool, Effector)

    dod = tool.define_done(5, {})
    assert dod["clarification_needed"] == []
    assert tool.act(5) == {"result": 10}

    assert tool.pre_load({"a": 1}) == {"a": 1}
    assert tool.gate({}) is True
    assert tool.upstream("x", {}) is None


class _ReadOnlyTool(BaseEffector):
    def define_done(
        self, request: Any, context: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "criteria": [{"name": "lookup_returned"}],
            "clarification_needed": [],
            "confidence": 1.0,
        }

    def act(self, request: Any) -> Any:
        return {"found": True}


def test_read_only_tool_does_not_need_to_override_gate_or_upstream():
    tool = _ReadOnlyTool()
    assert isinstance(tool, Effector)
    assert tool.act("anything") == {"found": True}
    assert tool.gate({"kind": "read"}) is True
