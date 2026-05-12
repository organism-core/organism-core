from __future__ import annotations

from pathlib import Path

import pytest

from organism.orchestrator import OrchestratorSettings
from organism.settings import discover_all_settings, get_settings_class


def test_default():
    s = OrchestratorSettings()
    assert s.autonomous_max_revision_attempts == 2


def test_custom():
    s = OrchestratorSettings(autonomous_max_revision_attempts=5)
    assert s.autonomous_max_revision_attempts == 5


def test_zero_attempts_ok():
    s = OrchestratorSettings(autonomous_max_revision_attempts=0)
    assert s.autonomous_max_revision_attempts == 0


def test_negative_attempts_raises():
    with pytest.raises(ValueError, match="autonomous_max_revision_attempts"):
        OrchestratorSettings(autonomous_max_revision_attempts=-1)


def test_round_trip(tmp_path: Path):
    path = tmp_path / "orch.yaml"
    original = OrchestratorSettings(autonomous_max_revision_attempts=4)
    original.save(path)
    assert OrchestratorSettings.load(path) == original


def test_registered():
    assert get_settings_class("orchestrator") is OrchestratorSettings
    assert "orchestrator" in discover_all_settings()
