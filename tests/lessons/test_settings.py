from __future__ import annotations

from pathlib import Path

import pytest

from organism.lessons import LessonsAggregatorSettings, LessonsSourceSettings
from organism.settings import discover_all_settings, get_settings_class


def test_aggregator_defaults():
    s = LessonsAggregatorSettings()
    assert s.query_max_results == 10


def test_aggregator_zero_max_results_raises():
    with pytest.raises(ValueError, match="query_max_results"):
        LessonsAggregatorSettings(query_max_results=0)


def test_aggregator_round_trip(tmp_path: Path):
    path = tmp_path / "agg.yaml"
    original = LessonsAggregatorSettings(query_max_results=25)
    original.save(path)
    assert LessonsAggregatorSettings.load(path) == original


def test_source_defaults():
    s = LessonsSourceSettings()
    assert s.max_confidence_delta == 0.5


def test_source_max_confidence_out_of_range_raises():
    with pytest.raises(ValueError, match="max_confidence_delta"):
        LessonsSourceSettings(max_confidence_delta=1.5)


def test_source_max_confidence_at_boundary_ok():
    LessonsSourceSettings(max_confidence_delta=0.0)
    LessonsSourceSettings(max_confidence_delta=1.0)


def test_source_round_trip(tmp_path: Path):
    path = tmp_path / "src.yaml"
    original = LessonsSourceSettings(max_confidence_delta=0.3)
    original.save(path)
    assert LessonsSourceSettings.load(path) == original


def test_aggregator_registered():
    assert (
        get_settings_class("lessons_aggregator")
        is LessonsAggregatorSettings
    )
    assert "lessons_aggregator" in discover_all_settings()


def test_source_registered():
    assert get_settings_class("lessons_source") is LessonsSourceSettings
    assert "lessons_source" in discover_all_settings()
