from __future__ import annotations

from pathlib import Path

from examples.architect_lite import run_demo as run_architect
from examples.architect_lite.demo import KIND as ARCH_KIND
from examples.cfo_lite import run_demo as run_cfo
from examples.cfo_lite.demo import KIND as CFO_KIND
from examples.tax_lite import run_demo as run_tax
from examples.tax_lite.demo import KIND as TAX_KIND


def _silent(_: str) -> None:
    return None


def test_all_three_demos_produce_identical_pipeline_counts(
    tmp_path: Path,
):
    arch = run_architect(tmp_path / "arch", print_fn=_silent)
    tax = run_tax(tmp_path / "tax", print_fn=_silent)
    cfo = run_cfo(tmp_path / "cfo", print_fn=_silent)

    # Trenn-Test als Test: drei Domaenen, identische Pipeline-Zaehler
    assert (
        arch.entities_seeded
        == tax.entities_seeded
        == cfo.entities_seeded
        == 3
    )
    assert (
        arch.actions_executed
        == tax.actions_executed
        == cfo.actions_executed
    )
    assert (
        arch.plans_proposed
        == tax.plans_proposed
        == cfo.plans_proposed
    )
    assert (
        arch.plans_applied == tax.plans_applied == cfo.plans_applied
    )
    assert (
        arch.traces_recorded
        == tax.traces_recorded
        == cfo.traces_recorded
    )
    assert (
        arch.lessons_recorded
        == tax.lessons_recorded
        == cfo.lessons_recorded
    )
    assert (
        arch.events_captured
        == tax.events_captured
        == cfo.events_captured
    )
    assert (
        arch.transitions_observed
        == tax.transitions_observed
        == cfo.transitions_observed
    )
    assert arch.final_stage == tax.final_stage == cfo.final_stage


def test_all_three_demos_produce_identical_event_breakdown(
    tmp_path: Path,
):
    arch = run_architect(tmp_path / "arch", print_fn=_silent)
    tax = run_tax(tmp_path / "tax", print_fn=_silent)
    cfo = run_cfo(tmp_path / "cfo", print_fn=_silent)

    assert arch.event_types == tax.event_types == cfo.event_types

    expected_types = {
        "plan_proposed",
        "lifecycle_transition",
        "trace_recorded",
        "lesson_recorded",
    }
    assert set(arch.event_types) == expected_types


def test_all_three_demos_use_distinct_kinds():
    assert ARCH_KIND != TAX_KIND
    assert TAX_KIND != CFO_KIND
    assert ARCH_KIND != CFO_KIND
    assert {ARCH_KIND, TAX_KIND, CFO_KIND} == {
        "extract_floor_plan",
        "validate_tax_return",
        "run_close_step",
    }


def test_all_three_demos_reach_autonomous_stage(tmp_path: Path):
    arch = run_architect(tmp_path / "arch", print_fn=_silent)
    tax = run_tax(tmp_path / "tax", print_fn=_silent)
    cfo = run_cfo(tmp_path / "cfo", print_fn=_silent)

    assert arch.final_stage == "autonomous"
    assert tax.final_stage == "autonomous"
    assert cfo.final_stage == "autonomous"


def test_all_three_demos_record_at_least_one_transition(tmp_path: Path):
    arch = run_architect(tmp_path / "arch", print_fn=_silent)
    tax = run_tax(tmp_path / "tax", print_fn=_silent)
    cfo = run_cfo(tmp_path / "cfo", print_fn=_silent)

    assert arch.transitions_observed >= 1
    assert tax.transitions_observed >= 1
    assert cfo.transitions_observed >= 1
