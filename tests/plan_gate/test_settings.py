from __future__ import annotations

from pathlib import Path

from organism.plan_gate import PlanGateSettings
from organism.settings import discover_all_settings, get_settings_class


def test_default():
    s = PlanGateSettings()
    assert s.require_decision_reason is False


def test_custom():
    s = PlanGateSettings(require_decision_reason=True)
    assert s.require_decision_reason is True


def test_round_trip(tmp_path: Path):
    path = tmp_path / "plan_gate.yaml"
    original = PlanGateSettings(require_decision_reason=True)
    original.save(path)
    loaded = PlanGateSettings.load(path)
    assert loaded == original


def test_registered_under_canonical_name():
    assert get_settings_class("plan_gate") is PlanGateSettings
    assert "plan_gate" in discover_all_settings()
