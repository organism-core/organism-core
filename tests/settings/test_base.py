from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from organism.settings import SettingsBase


@dataclass
class _ExampleSettings(SettingsBase):
    threshold: float = 0.8
    name: str = "default"
    enabled: bool = True


def test_defaults_when_no_path():
    s = _ExampleSettings.load()
    assert s.threshold == 0.8
    assert s.name == "default"
    assert s.enabled is True


def test_defaults_when_path_missing(tmp_path: Path):
    s = _ExampleSettings.load(tmp_path / "missing.yaml")
    assert s.threshold == 0.8
    assert s.name == "default"


def test_load_from_existing_file(tmp_path: Path):
    path = tmp_path / "x.yaml"
    path.write_text("threshold: 0.5\nname: custom\n")
    s = _ExampleSettings.load(path)
    assert s.threshold == 0.5
    assert s.name == "custom"
    assert s.enabled is True


def test_load_unknown_keys_are_filtered(tmp_path: Path):
    path = tmp_path / "x.yaml"
    path.write_text("threshold: 0.3\nfuture_field: ignored\n")
    s = _ExampleSettings.load(path)
    assert s.threshold == 0.3
    assert not hasattr(s, "future_field")


def test_load_missing_keys_use_defaults(tmp_path: Path):
    path = tmp_path / "x.yaml"
    path.write_text("threshold: 0.3\n")
    s = _ExampleSettings.load(path)
    assert s.threshold == 0.3
    assert s.name == "default"
    assert s.enabled is True


def test_load_empty_file_uses_defaults(tmp_path: Path):
    path = tmp_path / "x.yaml"
    path.write_text("")
    s = _ExampleSettings.load(path)
    assert s.threshold == 0.8


def test_load_non_mapping_raises(tmp_path: Path):
    path = tmp_path / "x.yaml"
    path.write_text("- just\n- a\n- list\n")
    with pytest.raises(ValueError, match="must contain a YAML mapping"):
        _ExampleSettings.load(path)


def test_save_creates_file(tmp_path: Path):
    path = tmp_path / "out.yaml"
    s = _ExampleSettings(threshold=0.9, name="x")
    s.save(path)
    assert path.exists()
    content = path.read_text()
    assert "threshold: 0.9" in content
    assert "name: x" in content


def test_save_creates_parent_directories(tmp_path: Path):
    path = tmp_path / "deep" / "nested" / "out.yaml"
    s = _ExampleSettings()
    s.save(path)
    assert path.exists()


def test_round_trip_preserves_values(tmp_path: Path):
    path = tmp_path / "rt.yaml"
    original = _ExampleSettings(threshold=0.42, name="round", enabled=False)
    original.save(path)
    loaded = _ExampleSettings.load(path)
    assert loaded == original


def test_to_dict_includes_all_fields():
    s = _ExampleSettings(threshold=0.1, name="t", enabled=False)
    assert s.to_dict() == {
        "threshold": 0.1,
        "name": "t",
        "enabled": False,
    }


def test_from_dict_reconstructs():
    s = _ExampleSettings.from_dict({"threshold": 0.2, "name": "f"})
    assert s.threshold == 0.2
    assert s.name == "f"
    assert s.enabled is True


class _NotADataclass(SettingsBase):
    pass


def test_to_dict_on_non_dataclass_raises():
    with pytest.raises(TypeError, match="must be a dataclass"):
        _NotADataclass().to_dict()


def test_from_dict_on_non_dataclass_raises():
    with pytest.raises(TypeError, match="must be a dataclass"):
        _NotADataclass.from_dict({})
