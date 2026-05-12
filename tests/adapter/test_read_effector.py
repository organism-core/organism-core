from typing import Any

import pytest

from organism.adapter import BaseEffector, Effector, ReadEffector


def test_read_effector_satisfies_protocol():
    assert isinstance(ReadEffector(), Effector)


def test_read_effector_inherits_from_base():
    assert issubclass(ReadEffector, BaseEffector)


def test_read_only_marker_true():
    assert ReadEffector.read_only is True


def test_base_effector_read_only_marker_false():
    assert BaseEffector.read_only is False


def test_pre_load_inherits_passthrough():
    re = ReadEffector()
    ctx = {"k": 1, "nested": {"x": 2}}
    assert re.pre_load(ctx) is ctx


def test_define_done_returns_empty_dict_not_blocker():
    """Reads don't need a safety-gate via DoD."""
    re = ReadEffector()
    dod = re.define_done("any-request", {})
    assert dod == {}


def test_act_still_raises():
    """Read logic must be implemented explicitly — no silent default."""
    with pytest.raises(NotImplementedError):
        ReadEffector().act("anything")


def test_upstream_inherits_silent_noop():
    assert ReadEffector().upstream("event", {"x": 1}) is None


def test_gate_allows():
    assert ReadEffector().gate({"kind": "read"}) is True


class _Lookup(ReadEffector):
    name = "lookup"

    def __init__(self, data: dict[str, Any]) -> None:
        self.data = dict(data)

    def act(self, request: Any) -> Any:
        return self.data.get(request)


def test_subclass_only_needs_to_override_act():
    tool = _Lookup({"alpha": 1, "beta": 2})
    assert isinstance(tool, Effector)
    assert tool.read_only is True

    # All other contacts inherited cleanly.
    assert tool.pre_load({"a": 1}) == {"a": 1}
    assert tool.define_done("alpha", {}) == {}
    assert tool.gate({"kind": "read"}) is True
    assert tool.upstream("event", {}) is None

    # The actual read works.
    assert tool.act("alpha") == 1
    assert tool.act("missing") is None


def test_subclass_can_override_read_only_marker_to_false():
    """A read-effector that gains side effects can flip the marker
    without rewriting the class hierarchy."""

    class _MutatingLookup(ReadEffector):
        read_only = False

        def act(self, request):
            return request

    assert _MutatingLookup().read_only is False


def test_subclass_can_set_class_attribute_name():
    """Confirms standard attribute pattern for `name` works as
    inherited by ReadEffector subclasses."""

    class _Named(ReadEffector):
        name = "my_named_lookup"

        def act(self, request):
            return None

    assert _Named().name == "my_named_lookup"
