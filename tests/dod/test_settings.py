from __future__ import annotations

from pathlib import Path

from organism.dod import DoDEngineSettings, EntityFrontmatterSettings
from organism.settings import discover_all_settings, get_settings_class


def test_dod_engine_settings_default():
    s = DoDEngineSettings()
    assert s.threshold == 0.8


def test_dod_engine_settings_custom():
    s = DoDEngineSettings(threshold=0.5)
    assert s.threshold == 0.5


def test_dod_engine_settings_round_trip(tmp_path: Path):
    path = tmp_path / "dod_engine.yaml"
    original = DoDEngineSettings(threshold=0.42)
    original.save(path)
    loaded = DoDEngineSettings.load(path)
    assert loaded == original


def test_entity_frontmatter_settings_default():
    s = EntityFrontmatterSettings()
    assert s.confidence_when_loaded == 0.5


def test_entity_frontmatter_settings_custom():
    s = EntityFrontmatterSettings(confidence_when_loaded=0.9)
    assert s.confidence_when_loaded == 0.9


def test_entity_frontmatter_settings_round_trip(tmp_path: Path):
    path = tmp_path / "ef.yaml"
    original = EntityFrontmatterSettings(confidence_when_loaded=0.33)
    original.save(path)
    loaded = EntityFrontmatterSettings.load(path)
    assert loaded == original


def test_dod_engine_registered():
    assert get_settings_class("dod_engine") is DoDEngineSettings


def test_entity_frontmatter_registered():
    assert get_settings_class("entity_frontmatter") is EntityFrontmatterSettings


def test_both_visible_in_discovery():
    all_settings = discover_all_settings()
    assert "dod_engine" in all_settings
    assert "entity_frontmatter" in all_settings
