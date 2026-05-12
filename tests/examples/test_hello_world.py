from __future__ import annotations

from pathlib import Path

from examples.hello_world import run_demo
from examples.hello_world.demo import ENTITY_ID, KIND


def _silent(_: str) -> None:
    return None


def test_demo_runs_deterministic_without_api_key(tmp_path: Path):
    # Force deterministic mode by passing an empty api_key, so the
    # test never tries to import or call ``anthropic``.
    summary = run_demo(tmp_path, print_fn=_silent, api_key="")
    assert summary.mode == "deterministic"


def test_demo_produces_a_greeting(tmp_path: Path):
    summary = run_demo(tmp_path, print_fn=_silent, api_key="")
    assert "Hello" in summary.greeting
    assert "Adopter" in summary.greeting


def test_demo_score_is_perfect_in_deterministic_mode(tmp_path: Path):
    summary = run_demo(tmp_path, print_fn=_silent, api_key="")
    assert summary.score == 1.0
    assert summary.all_satisfied is True


def test_demo_runs_all_three_criteria(tmp_path: Path):
    summary = run_demo(tmp_path, print_fn=_silent, api_key="")
    names = {name for name, _, _ in summary.criteria_results}
    assert names == {"mentions_name", "length", "friendly_tone"}


def test_demo_creates_expected_directories(tmp_path: Path):
    # hello_world deliberately omits the lessons feedback loop, so
    # the lessons/ directory is not exercised here. The four stores
    # that the single propose -> approve -> apply cycle touches are:
    run_demo(tmp_path, print_fn=_silent, api_key="")
    for sub in ("entities", "plans", "lifecycle", "traces"):
        assert (tmp_path / sub).exists()


def test_demo_uses_greet_user_kind():
    assert KIND == "greet_user"
    assert ENTITY_ID == "world"


def test_demo_print_fn_receives_narration(tmp_path: Path):
    captured: list[str] = []
    run_demo(tmp_path, print_fn=captured.append, api_key="")
    output = "\n".join(captured)
    assert "hello_world" in output
    assert "[SETUP]" in output
    assert "[VALIDATION]" in output
    assert "deterministic" in output
