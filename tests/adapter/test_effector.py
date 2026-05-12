from typing import Any

from organism.adapter import Effector


class CompleteTool:
    def pre_load(self, context: dict[str, Any]) -> dict[str, Any]:
        return context

    def define_done(
        self, request: Any, context: dict[str, Any]
    ) -> dict[str, Any]:
        return {"criteria": [], "clarification_needed": []}

    def act(self, request: Any) -> Any:
        return {"ok": True}

    def upstream(self, kind: str, payload: dict[str, Any]) -> None:
        pass

    def gate(self, action: dict[str, Any]) -> bool:
        return True


class MissingDefineDone:
    def pre_load(self, context: dict[str, Any]) -> dict[str, Any]:
        return context

    def act(self, request: Any) -> Any:
        return None

    def upstream(self, kind: str, payload: dict[str, Any]) -> None:
        pass

    def gate(self, action: dict[str, Any]) -> bool:
        return True


class MissingAct:
    def pre_load(self, context: dict[str, Any]) -> dict[str, Any]:
        return context

    def define_done(
        self, request: Any, context: dict[str, Any]
    ) -> dict[str, Any]:
        return {}

    def upstream(self, kind: str, payload: dict[str, Any]) -> None:
        pass

    def gate(self, action: dict[str, Any]) -> bool:
        return True


def test_tool_with_all_five_contacts_satisfies_protocol():
    assert isinstance(CompleteTool(), Effector)


def test_tool_missing_define_done_fails_protocol():
    assert not isinstance(MissingDefineDone(), Effector)


def test_tool_missing_act_fails_protocol():
    assert not isinstance(MissingAct(), Effector)


def test_unrelated_object_fails_protocol():
    assert not isinstance(object(), Effector)
    assert not isinstance("string", Effector)


def test_complete_tool_methods_callable():
    tool = CompleteTool()
    assert tool.pre_load({"k": 1}) == {"k": 1}
    assert tool.define_done("req", {}) == {
        "criteria": [],
        "clarification_needed": [],
    }
    assert tool.act("req") == {"ok": True}
    tool.upstream("lesson", {"x": 1})
    assert tool.gate({"kind": "write"}) is True
