from __future__ import annotations

from dataclasses import dataclass

import pytest

from organism.settings import (
    SettingsBase,
    discover_all_settings,
    get_settings_class,
    is_registered,
    register_settings,
)


@dataclass
class _RegistryTestA(SettingsBase):
    x: int = 1


@dataclass
class _RegistryTestB(SettingsBase):
    y: int = 2


def test_register_and_discover():
    register_settings("registry_test_alpha")(_RegistryTestA)
    register_settings("registry_test_beta")(_RegistryTestB)

    all_settings = discover_all_settings()
    assert all_settings["registry_test_alpha"] is _RegistryTestA
    assert all_settings["registry_test_beta"] is _RegistryTestB


def test_get_settings_class():
    register_settings("registry_test_get")(_RegistryTestA)
    assert get_settings_class("registry_test_get") is _RegistryTestA


def test_get_unknown_raises():
    with pytest.raises(KeyError, match="No settings registered"):
        get_settings_class("never_registered_name")


def test_is_registered():
    assert not is_registered("registry_test_unique_check")

    @register_settings("registry_test_unique_check")
    @dataclass
    class _Local(SettingsBase):
        v: int = 0

    assert is_registered("registry_test_unique_check")


def test_duplicate_same_class_is_idempotent():
    register_settings("registry_test_idempotent")(_RegistryTestA)
    register_settings("registry_test_idempotent")(_RegistryTestA)
    assert get_settings_class("registry_test_idempotent") is _RegistryTestA


def test_duplicate_different_class_raises():
    register_settings("registry_test_conflict")(_RegistryTestA)
    with pytest.raises(ValueError, match="already registered"):
        register_settings("registry_test_conflict")(_RegistryTestB)


def test_discover_returns_copy():
    snapshot = discover_all_settings()
    snapshot["mutated"] = _RegistryTestA
    assert "mutated" not in discover_all_settings()


def test_decorator_returns_class_unchanged():
    @register_settings("registry_test_decorator_returns")
    @dataclass
    class _MySettings(SettingsBase):
        x: int = 5

    instance = _MySettings(x=10)
    assert instance.x == 10
    assert _MySettings.__name__ == "_MySettings"
