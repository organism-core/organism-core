from __future__ import annotations

from pathlib import Path

from examples.cfo_lite import run_demo
from examples.cfo_lite.demo import KIND


def _silent(_: str) -> None:
    return None


def test_demo_completes(tmp_path: Path):
    summary = run_demo(tmp_path, print_fn=_silent)
    assert summary.entities_seeded == 3
    assert summary.actions_executed >= 5
    assert summary.plans_proposed == 1
    assert summary.plans_applied == 1


def test_demo_creates_expected_directories(tmp_path: Path):
    run_demo(tmp_path, print_fn=_silent)
    for sub in ("entities", "plans", "lifecycle", "lessons", "traces"):
        assert (tmp_path / sub).exists()


def test_demo_records_traces(tmp_path: Path):
    summary = run_demo(tmp_path, print_fn=_silent)
    assert summary.traces_recorded >= 6


def test_demo_records_lessons(tmp_path: Path):
    summary = run_demo(tmp_path, print_fn=_silent)
    assert summary.lessons_recorded == 3


def test_demo_captures_all_event_types(tmp_path: Path):
    summary = run_demo(tmp_path, print_fn=_silent)
    assert "plan_proposed" in summary.event_types
    assert "trace_recorded" in summary.event_types
    assert "lesson_recorded" in summary.event_types
    assert "lifecycle_transition" in summary.event_types


def test_demo_final_stage_is_autonomous(tmp_path: Path):
    summary = run_demo(tmp_path, print_fn=_silent)
    assert summary.final_stage == "autonomous"


def test_demo_uses_run_close_step_kind(tmp_path: Path):
    assert KIND == "run_close_step"


def test_demo_print_fn_receives_output(tmp_path: Path):
    captured: list[str] = []
    run_demo(tmp_path, print_fn=captured.append)
    output = "\n".join(captured)
    assert "cfo_lite" in output
    assert "[SETUP]" in output
    assert "Perioden" in output


def test_demo_observes_at_least_one_transition(tmp_path: Path):
    summary = run_demo(tmp_path, print_fn=_silent)
    assert summary.transitions_observed >= 1
