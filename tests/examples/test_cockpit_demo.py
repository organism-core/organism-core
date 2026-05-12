from __future__ import annotations

from pathlib import Path

from examples.cockpit_demo import run_demo


def _silent(_: str) -> None:
    return None


def test_cockpit_demo_runs(tmp_path: Path):
    summary = run_demo(tmp_path, print_fn=_silent)
    assert summary.kinds_seeded == 3
    assert summary.actions_executed >= 6
    assert summary.summary_rows == 3


def test_cockpit_demo_produces_pending_revision_escalation_plan(tmp_path: Path):
    summary = run_demo(tmp_path, print_fn=_silent)
    assert summary.pending_plans_count >= 1


def test_cockpit_demo_surfaces_drift_warning(tmp_path: Path):
    summary = run_demo(tmp_path, print_fn=_silent)
    assert summary.drift_warnings >= 1


def test_cockpit_demo_captures_ui_events_with_severities(tmp_path: Path):
    summary = run_demo(tmp_path, print_fn=_silent)
    assert summary.ui_events_captured >= 1
    assert summary.ui_event_severities
