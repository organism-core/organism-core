from __future__ import annotations

from pathlib import Path

from examples.full_recherche import run_demo


def _silent(_: str) -> None:
    return None


def test_full_recherche_runs_all_six_sources(tmp_path: Path):
    summary = run_demo(tmp_path, print_fn=_silent)
    assert summary.primary_seeded is True
    assert summary.siblings_seeded == 2
    assert summary.lesson_pre_seeded is True
    assert summary.sources_count == 6


def test_full_recherche_five_of_six_sources_contribute_criteria(tmp_path: Path):
    """user_clarification is the fallback path; with the demo's wiring,
    upstream provides ample criteria, so clarification does not trigger.
    The other five sources each contribute at least one criterion.
    """
    summary = run_demo(tmp_path, print_fn=_silent)
    assert summary.sources_contributing == 5
    assert set(summary.contributions_per_source.keys()) == {
        "entity_frontmatter",
        "lessons",
        "related_entities",
        "vector_search",
        "domain_pattern",
    }


def test_full_recherche_assembles_seven_criteria(tmp_path: Path):
    summary = run_demo(tmp_path, print_fn=_silent)
    # 1 (frontmatter) + 1 (lesson) + 2 (siblings) + 2 (vector) + 1 (pattern)
    # = 7 deduped criteria.
    assert summary.total_criteria == 7
    assert summary.contributions_per_source["entity_frontmatter"] == 1
    assert summary.contributions_per_source["lessons"] == 1
    assert summary.contributions_per_source["related_entities"] == 2
    assert summary.contributions_per_source["vector_search"] == 2
    assert summary.contributions_per_source["domain_pattern"] == 1


def test_full_recherche_confidence_caps_at_one(tmp_path: Path):
    summary = run_demo(tmp_path, print_fn=_silent)
    # 0.5 + 0.1 + 0.2 + 0.1 + 0.1 = 1.0 (capped); user_clarification 0.
    assert summary.final_confidence == 1.0


def test_full_recherche_dedupe_excludes_already_present_criteria(
    tmp_path: Path,
):
    """The doors_aligned criterion is in two siblings — should appear
    exactly once in the assembled DoD."""
    summary = run_demo(tmp_path, print_fn=_silent)
    # related_entities sees doors_aligned twice (sibling-a + sibling-b)
    # but contributes it once.
    assert summary.contributions_per_source["related_entities"] == 2
