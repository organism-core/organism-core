from __future__ import annotations

from pathlib import Path

from examples.architect_lite import run_demo
from examples.architect_lite.demo import KIND


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
    # 1 propose + 1 apply + 3 checked-execute + 1 autonomous = 6 traces
    assert summary.traces_recorded >= 6


def test_demo_records_lessons(tmp_path: Path):
    summary = run_demo(tmp_path, print_fn=_silent)
    # 2 revision-lessons (max_attempts=2) + 1 manual = 3
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


def test_demo_observes_at_least_one_transition(tmp_path: Path):
    summary = run_demo(tmp_path, print_fn=_silent)
    # Step 2 should promote checked -> routine after 3 successful actions
    assert summary.transitions_observed >= 1


def test_demo_revision_attempts_recorded(tmp_path: Path):
    summary = run_demo(tmp_path, print_fn=_silent)
    # 2 revision attempts means 2 revision lessons + 1 hitl = 3 total
    assert summary.lessons_recorded == 3


def test_demo_uses_extract_floor_plan_kind(tmp_path: Path):
    # Sanity: KIND constant matches what we expect downstream
    assert KIND == "extract_floor_plan"


def test_demo_print_fn_receives_output(tmp_path: Path):
    captured: list[str] = []
    run_demo(tmp_path, print_fn=captured.append)
    output = "\n".join(captured)
    assert "architect_lite" in output
    assert "[SETUP]" in output
    assert "[SEEDING]" in output
    assert "[STEP 1]" in output
    assert "[STEP 4]" in output
    assert "[SUMMARY]" in output
