from __future__ import annotations

from typing import Callable, TypeVar

from organism.settings.base import SettingsBase

T = TypeVar("T", bound=SettingsBase)

_REGISTRY: dict[str, type[SettingsBase]] = {}


def register_settings(name: str) -> Callable[[type[T]], type[T]]:
    def decorator(cls: type[T]) -> type[T]:
        existing = _REGISTRY.get(name)
        if existing is not None and existing is not cls:
            raise ValueError(
                f"Settings name '{name}' already registered to "
                f"{existing.__name__}; cannot re-register to {cls.__name__}"
            )
        _REGISTRY[name] = cls
        return cls

    return decorator


def discover_all_settings() -> dict[str, type[SettingsBase]]:
    return dict(_REGISTRY)


def get_settings_class(name: str) -> type[SettingsBase]:
    if name not in _REGISTRY:
        raise KeyError(f"No settings registered under name '{name}'")
    return _REGISTRY[name]


def is_registered(name: str) -> bool:
    return name in _REGISTRY


def clear_registry() -> None:
    _REGISTRY.clear()
