from __future__ import annotations

from pathlib import Path

import pytest

from organism.lifecycle import LifecycleSettings
from organism.settings import discover_all_settings, get_settings_class


def test_defaults():
    s = LifecycleSettings()
    assert s.initial_stage == "proposed"
    assert s.promote_after_n == 30
    assert s.promote_score_threshold == 0.9
    assert s.demote_after_n == 5
    assert s.demote_score_threshold == 0.7
    assert s.window_size == 50


def test_custom_values():
    s = LifecycleSettings(
        initial_stage="checked",
        promote_after_n=10,
        promote_score_threshold=0.95,
        demote_after_n=3,
        demote_score_threshold=0.5,
        window_size=20,
    )
    assert s.initial_stage == "checked"
    assert s.promote_after_n == 10


def test_invalid_initial_stage_raises():
    with pytest.raises(ValueError, match="initial_stage must be"):
        LifecycleSettings(initial_stage="not_a_stage")


def test_zero_promote_after_n_raises():
    with pytest.raises(ValueError, match="promote_after_n must be > 0"):
        LifecycleSettings(promote_after_n=0)


def test_zero_demote_after_n_raises():
    with pytest.raises(ValueError, match="demote_after_n must be > 0"):
        LifecycleSettings(demote_after_n=0)


def test_window_smaller_than_promote_window_raises():
    with pytest.raises(ValueError, match="window_size must be"):
        LifecycleSettings(promote_after_n=100, window_size=50)


def test_window_smaller_than_demote_window_raises():
    with pytest.raises(ValueError, match="window_size must be"):
        LifecycleSettings(demote_after_n=100, window_size=50)


def test_promote_score_threshold_out_of_range_raises():
    with pytest.raises(ValueError, match="promote_score_threshold must be in"):
        LifecycleSettings(promote_score_threshold=1.5)


def test_demote_score_threshold_out_of_range_raises():
    with pytest.raises(ValueError, match="demote_score_threshold must be in"):
        LifecycleSettings(demote_score_threshold=-0.1)


def test_round_trip(tmp_path: Path):
    path = tmp_path / "lifecycle.yaml"
    original = LifecycleSettings(
        initial_stage="checked",
        promote_after_n=20,
        demote_score_threshold=0.6,
        window_size=40,
    )
    original.save(path)
    loaded = LifecycleSettings.load(path)
    assert loaded == original


def test_registered_under_canonical_name():
    assert get_settings_class("lifecycle") is LifecycleSettings
    assert "lifecycle" in discover_all_settings()
