from __future__ import annotations

from pathlib import Path

import pytest

from organism.observability import TraceStoreSettings
from organism.settings import discover_all_settings, get_settings_class


def test_defaults():
    s = TraceStoreSettings()
    assert s.enabled is True
    assert s.summary_max_length == 500


def test_custom():
    s = TraceStoreSettings(enabled=False, summary_max_length=100)
    assert s.enabled is False
    assert s.summary_max_length == 100


def test_negative_max_length_raises():
    with pytest.raises(ValueError, match="summary_max_length must be"):
        TraceStoreSettings(summary_max_length=-1)


def test_zero_max_length_ok():
    TraceStoreSettings(summary_max_length=0)


def test_round_trip(tmp_path: Path):
    path = tmp_path / "trace_store.yaml"
    original = TraceStoreSettings(enabled=False, summary_max_length=200)
    original.save(path)
    loaded = TraceStoreSettings.load(path)
    assert loaded == original


def test_registered():
    assert get_settings_class("trace_store") is TraceStoreSettings
    assert "trace_store" in discover_all_settings()
