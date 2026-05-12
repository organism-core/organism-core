from __future__ import annotations

from dataclasses import asdict, fields, is_dataclass
from pathlib import Path
from typing import Any, TypeVar

import yaml

T = TypeVar("T", bound="SettingsBase")


class SettingsBase:
    """Mixin for dataclass settings with YAML round-trip and lenient from_dict.

    Subclasses must be decorated with @dataclass and have defaults on every
    field — otherwise load(path=None) and load(missing-path) cannot construct
    the defaults instance.

    from_dict is intentionally lenient: unknown keys are dropped (forward-
    compatible YAML evolution), missing keys fall back to dataclass defaults.
    """

    @classmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T:
        if not is_dataclass(cls):
            raise TypeError(
                f"{cls.__name__} must be a dataclass to use SettingsBase"
            )
        known = {f.name for f in fields(cls)}
        kwargs = {k: v for k, v in data.items() if k in known}
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        if not is_dataclass(self):
            raise TypeError(
                f"{type(self).__name__} must be a dataclass to use SettingsBase"
            )
        return asdict(self)

    @classmethod
    def load(cls: type[T], path: Path | str | None = None) -> T:
        if path is None:
            return cls()
        p = Path(path)
        if not p.exists():
            return cls()
        text = p.read_text(encoding="utf-8")
        data = yaml.safe_load(text) or {}
        if not isinstance(data, dict):
            raise ValueError(
                f"Settings file {p} must contain a YAML mapping, got "
                f"{type(data).__name__}"
            )
        return cls.from_dict(data)

    def save(self, path: Path | str) -> None:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            yaml.safe_dump(
                self.to_dict(),
                sort_keys=False,
                allow_unicode=True,
                default_flow_style=False,
            ),
            encoding="utf-8",
        )
