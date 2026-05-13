from __future__ import annotations

from pathlib import Path

import pytest

from organism.dod import (
    CROSS_KIND_CRITERION_SOURCE,
    Criterion,
    CrossDomainLessonsSource,
    DoD,
    DoDEngine,
    DoDSource,
)
from organism.dod.sources.lessons import CONTEXT_KEY_KIND as LESSONS_KIND_KEY
from organism.lessons import LessonsAggregator, LessonsStore


def _aggregator(tmp_path: Path) -> LessonsAggregator:
    return LessonsAggregator(store=LessonsStore(tmp_path / "lessons"))


def _seed_lesson(
    aggregator: LessonsAggregator,
    *,
    kind: str,
    context_pattern: dict,
    criterion_name: str,
    criterion_weight: float = 1.0,
):
    aggregator.record_lesson(
        kind=kind,
        observation=f"lesson for {kind}",
        criteria_hint=[
            Criterion(
                name=criterion_name,
                expected=True,
                weight=criterion_weight,
            )
        ],
        context_pattern=context_pattern,
    )


# ---------- Aggregator.query_cross_kind


def test_aggregator_query_cross_kind_excludes_current_kind(tmp_path: Path):
    agg = _aggregator(tmp_path)
    _seed_lesson(
        agg, kind="k1", context_pattern={"domain": "alpha"}, criterion_name="a"
    )
    _seed_lesson(
        agg, kind="k2", context_pattern={"domain": "alpha"}, criterion_name="b"
    )

    result = agg.query_cross_kind(
        exclude_kind="k1",
        context={"domain": "alpha"},
        match_keys=["domain"],
    )
    kinds = [l.kind for l in result]
    assert "k1" not in kinds
    assert "k2" in kinds


def test_aggregator_query_cross_kind_requires_match_keys(tmp_path: Path):
    agg = _aggregator(tmp_path)
    _seed_lesson(
        agg, kind="k1", context_pattern={"domain": "alpha"}, criterion_name="a"
    )
    result = agg.query_cross_kind(
        exclude_kind="other",
        context={"domain": "alpha"},
        match_keys=[],
    )
    assert result == []  # empty match_keys = no transfer


def test_aggregator_query_cross_kind_filters_on_all_match_keys(
    tmp_path: Path,
):
    agg = _aggregator(tmp_path)
    _seed_lesson(
        agg,
        kind="k1",
        context_pattern={"domain": "alpha", "subtype": "wide"},
        criterion_name="a",
    )
    _seed_lesson(
        agg,
        kind="k2",
        context_pattern={"domain": "alpha", "subtype": "narrow"},
        criterion_name="b",
    )

    # Only the wide-domain lesson matches.
    result = agg.query_cross_kind(
        exclude_kind="ignore",
        context={"domain": "alpha", "subtype": "wide"},
        match_keys=["domain", "subtype"],
    )
    assert [l.kind for l in result] == ["k1"]


def test_aggregator_query_cross_kind_missing_key_fails_match(
    tmp_path: Path,
):
    agg = _aggregator(tmp_path)
    _seed_lesson(
        agg,
        kind="k1",
        context_pattern={"domain": "alpha"},  # no 'subtype'
        criterion_name="a",
    )
    # Request supplies subtype, lesson doesn't — must NOT match.
    result = agg.query_cross_kind(
        exclude_kind="ignore",
        context={"domain": "alpha", "subtype": "wide"},
        match_keys=["domain", "subtype"],
    )
    assert result == []


def test_aggregator_query_cross_kind_respects_max_results(tmp_path: Path):
    agg = _aggregator(tmp_path)
    for i in range(5):
        _seed_lesson(
            agg,
            kind=f"k{i}",
            context_pattern={"domain": "alpha"},
            criterion_name=f"c{i}",
        )
    result = agg.query_cross_kind(
        exclude_kind="ignore",
        context={"domain": "alpha"},
        match_keys=["domain"],
        max_results=3,
    )
    assert len(result) == 3


# ---------- CrossDomainLessonsSource


def test_source_satisfies_protocol():
    src = CrossDomainLessonsSource(aggregator=None, match_keys=["domain"])
    assert isinstance(src, DoDSource)


def test_source_no_aggregator_yields_empty_contribution():
    src = CrossDomainLessonsSource(aggregator=None, match_keys=["domain"])
    contribution = src.contribute(
        "req", {LESSONS_KIND_KEY: "k", "domain": "alpha"}, DoD()
    )
    assert contribution.criteria == []
    assert contribution.confidence_delta == 0.0


def test_source_empty_match_keys_yields_empty_contribution(tmp_path: Path):
    agg = _aggregator(tmp_path)
    _seed_lesson(
        agg, kind="k1", context_pattern={"domain": "alpha"}, criterion_name="a"
    )
    src = CrossDomainLessonsSource(aggregator=agg, match_keys=[])
    contribution = src.contribute(
        "req", {LESSONS_KIND_KEY: "k2", "domain": "alpha"}, DoD()
    )
    assert contribution.criteria == []


def test_source_no_kind_in_context_yields_empty(tmp_path: Path):
    agg = _aggregator(tmp_path)
    _seed_lesson(
        agg, kind="k1", context_pattern={"domain": "alpha"}, criterion_name="a"
    )
    src = CrossDomainLessonsSource(
        aggregator=agg, match_keys=["domain"]
    )
    contribution = src.contribute("req", {"domain": "alpha"}, DoD())  # no kind
    assert contribution.criteria == []


def test_source_contributes_criteria_from_other_kind(tmp_path: Path):
    agg = _aggregator(tmp_path)
    _seed_lesson(
        agg,
        kind="other_kind",
        context_pattern={"domain": "alpha"},
        criterion_name="cross_criterion",
        criterion_weight=1.0,
    )
    src = CrossDomainLessonsSource(
        aggregator=agg,
        match_keys=["domain"],
        cross_kind_weight_factor=0.3,
    )
    contribution = src.contribute(
        "req",
        {LESSONS_KIND_KEY: "current_kind", "domain": "alpha"},
        DoD(),
    )
    assert len(contribution.criteria) == 1
    c = contribution.criteria[0]
    assert c.name == "cross_criterion"
    assert c.weight == pytest.approx(0.3)  # 1.0 * 0.3
    assert c.source == CROSS_KIND_CRITERION_SOURCE


def test_source_excludes_self_kind_lessons(tmp_path: Path):
    agg = _aggregator(tmp_path)
    _seed_lesson(
        agg,
        kind="my_kind",
        context_pattern={"domain": "alpha"},
        criterion_name="own_criterion",
    )
    src = CrossDomainLessonsSource(
        aggregator=agg, match_keys=["domain"]
    )
    contribution = src.contribute(
        "req",
        {LESSONS_KIND_KEY: "my_kind", "domain": "alpha"},
        DoD(),
    )
    # The lesson is from the same kind — must NOT be transferred.
    assert contribution.criteria == []


def test_source_dedupes_against_existing_criteria(tmp_path: Path):
    agg = _aggregator(tmp_path)
    _seed_lesson(
        agg,
        kind="other",
        context_pattern={"domain": "alpha"},
        criterion_name="already_present",
    )
    src = CrossDomainLessonsSource(
        aggregator=agg, match_keys=["domain"]
    )
    current = DoD(criteria=[Criterion(name="already_present", expected=True)])
    contribution = src.contribute(
        "req",
        {LESSONS_KIND_KEY: "current", "domain": "alpha"},
        current,
    )
    assert contribution.criteria == []


def test_source_evidence_includes_contributing_kinds(tmp_path: Path):
    agg = _aggregator(tmp_path)
    _seed_lesson(
        agg, kind="k_a", context_pattern={"domain": "alpha"}, criterion_name="a"
    )
    _seed_lesson(
        agg, kind="k_b", context_pattern={"domain": "alpha"}, criterion_name="b"
    )
    src = CrossDomainLessonsSource(
        aggregator=agg, match_keys=["domain"]
    )
    contribution = src.contribute(
        "req",
        {LESSONS_KIND_KEY: "current", "domain": "alpha"},
        DoD(),
    )
    assert set(contribution.evidence["contributing_kinds"]) == {"k_a", "k_b"}
    assert contribution.evidence["lessons_found"] == 2


def test_source_confidence_delta_only_when_criteria_contributed(
    tmp_path: Path,
):
    agg = _aggregator(tmp_path)
    src = CrossDomainLessonsSource(
        aggregator=agg, match_keys=["domain"], confidence_delta=0.5
    )
    # No lessons recorded — no contribution.
    contribution = src.contribute(
        "req",
        {LESSONS_KIND_KEY: "current", "domain": "alpha"},
        DoD(),
    )
    assert contribution.confidence_delta == 0.0


def test_source_rejects_invalid_confidence_delta():
    with pytest.raises(ValueError, match="confidence_delta"):
        CrossDomainLessonsSource(
            aggregator=None, match_keys=["x"], confidence_delta=2.0
        )


def test_source_rejects_invalid_weight_factor():
    with pytest.raises(ValueError, match="cross_kind_weight_factor"):
        CrossDomainLessonsSource(
            aggregator=None,
            match_keys=["x"],
            cross_kind_weight_factor=1.5,
        )


def test_source_rejects_invalid_max_results():
    with pytest.raises(ValueError, match="max_results"):
        CrossDomainLessonsSource(
            aggregator=None, match_keys=["x"], max_results=0
        )


# ---------- Integration


def test_engine_picks_up_cross_domain_criteria(tmp_path: Path):
    """End-to-end: lesson recorded under k1 (with domain=alpha) flows
    into a DoD derived for k2 (also domain=alpha) when the engine has
    CrossDomainLessonsSource wired."""
    agg = _aggregator(tmp_path)
    _seed_lesson(
        agg,
        kind="k1",
        context_pattern={"domain": "alpha"},
        criterion_name="transferable_criterion",
        criterion_weight=1.0,
    )

    engine = DoDEngine(
        sources=[
            CrossDomainLessonsSource(
                aggregator=agg,
                match_keys=["domain"],
                confidence_delta=1.0,
                cross_kind_weight_factor=0.5,
            )
        ]
    )
    dod = engine.derive(
        request="r", context={LESSONS_KIND_KEY: "k2", "domain": "alpha"}
    )
    names = [c.name for c in dod.criteria]
    assert "transferable_criterion" in names
    transferred = next(c for c in dod.criteria if c.name == "transferable_criterion")
    assert transferred.weight == pytest.approx(0.5)


def test_engine_no_transfer_when_domain_differs(tmp_path: Path):
    agg = _aggregator(tmp_path)
    _seed_lesson(
        agg,
        kind="k1",
        context_pattern={"domain": "alpha"},
        criterion_name="alpha_criterion",
    )

    engine = DoDEngine(
        sources=[
            CrossDomainLessonsSource(
                aggregator=agg,
                match_keys=["domain"],
                confidence_delta=1.0,
            )
        ]
    )
    # Request is in domain=beta — no match against the alpha lesson.
    dod = engine.derive(
        request="r", context={LESSONS_KIND_KEY: "k2", "domain": "beta"}
    )
    assert all(c.name != "alpha_criterion" for c in dod.criteria)
