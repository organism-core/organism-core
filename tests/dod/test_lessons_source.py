from __future__ import annotations

from pathlib import Path

import pytest

from organism.dod import (
    Criterion,
    DoD,
    DoDEngine,
    DoDEngineSettings,
    DoDSource,
    LessonsSource,
)
from organism.dod.sources.lessons import CONTEXT_KEY_KIND
from organism.lessons import (
    LessonsAggregator,
    LessonsSourceSettings,
    LessonsStore,
)


def _make_source(
    tmp_path: Path,
    *,
    with_aggregator: bool = True,
    **settings_kwargs,
) -> tuple[LessonsSource, LessonsAggregator | None]:
    aggregator = (
        LessonsAggregator(store=LessonsStore(tmp_path / "lessons"))
        if with_aggregator
        else None
    )
    settings = (
        LessonsSourceSettings(**settings_kwargs)
        if settings_kwargs
        else None
    )
    return LessonsSource(aggregator=aggregator, settings=settings), aggregator


def test_source_satisfies_protocol(tmp_path: Path):
    source, _ = _make_source(tmp_path)
    assert isinstance(source, DoDSource)


def test_no_aggregator_yields_silent_contribution(tmp_path: Path):
    source, _ = _make_source(tmp_path, with_aggregator=False)
    contribution = source.contribute(
        request="any", context={CONTEXT_KEY_KIND: "k"}, current=DoD()
    )
    assert contribution.criteria == []
    assert contribution.confidence_delta == 0.0
    assert contribution.evidence == {}


def test_no_kind_in_context_yields_silent(tmp_path: Path):
    source, _ = _make_source(tmp_path)
    contribution = source.contribute(
        request="any", context={}, current=DoD()
    )
    assert contribution.criteria == []
    assert contribution.evidence == {}


def test_no_lessons_for_kind_records_evidence(tmp_path: Path):
    source, _ = _make_source(tmp_path)
    contribution = source.contribute(
        request="any", context={CONTEXT_KEY_KIND: "k"}, current=DoD()
    )
    assert contribution.criteria == []
    assert contribution.evidence == {
        "queried_kind": "k",
        "lessons_found": 0,
    }


def test_lesson_criteria_emitted_into_contribution(tmp_path: Path):
    source, aggregator = _make_source(tmp_path)
    aggregator.record_lesson(
        kind="k",
        observation="add x",
        criteria_hint=[Criterion(name="x", expected=1, weight=1.0)],
        confidence_delta=0.1,
    )
    contribution = source.contribute(
        request="any", context={CONTEXT_KEY_KIND: "k"}, current=DoD()
    )
    assert [c.name for c in contribution.criteria] == ["x"]
    assert contribution.confidence_delta == 0.1
    assert contribution.evidence["lessons_found"] == 1


def test_multiple_lessons_aggregate_criteria(tmp_path: Path):
    source, aggregator = _make_source(tmp_path)
    aggregator.record_lesson(
        kind="k",
        observation="L1",
        criteria_hint=[Criterion(name="a", expected=1)],
        confidence_delta=0.1,
    )
    aggregator.record_lesson(
        kind="k",
        observation="L2",
        criteria_hint=[Criterion(name="b", expected=2)],
        confidence_delta=0.2,
    )
    contribution = source.contribute(
        request="any", context={CONTEXT_KEY_KIND: "k"}, current=DoD()
    )
    assert {c.name for c in contribution.criteria} == {"a", "b"}
    assert contribution.confidence_delta == pytest.approx(0.3)


def test_confidence_capped_by_settings(tmp_path: Path):
    source, aggregator = _make_source(
        tmp_path, max_confidence_delta=0.2
    )
    for i in range(5):
        aggregator.record_lesson(
            kind="k",
            observation=f"L{i}",
            confidence_delta=0.5,
        )
    contribution = source.contribute(
        request="any", context={CONTEXT_KEY_KIND: "k"}, current=DoD()
    )
    assert contribution.confidence_delta == 0.2


def test_lessons_filtered_by_context_pattern(tmp_path: Path):
    source, aggregator = _make_source(tmp_path)
    aggregator.record_lesson(
        kind="k",
        observation="match",
        criteria_hint=[Criterion(name="match", expected=True)],
        context_pattern={"type": "alpha"},
    )
    aggregator.record_lesson(
        kind="k",
        observation="no match",
        criteria_hint=[Criterion(name="other", expected=True)],
        context_pattern={"type": "beta"},
    )
    contribution = source.contribute(
        request="any",
        context={CONTEXT_KEY_KIND: "k", "type": "alpha"},
        current=DoD(),
    )
    assert [c.name for c in contribution.criteria] == ["match"]


def test_engine_integration_with_lessons(tmp_path: Path):
    source, aggregator = _make_source(tmp_path)
    aggregator.record_lesson(
        kind="k",
        observation="rule",
        criteria_hint=[
            Criterion(name="must_be_present", expected=True, weight=1.0),
        ],
        confidence_delta=0.4,
    )
    engine = DoDEngine(
        sources=[source],
        settings=DoDEngineSettings(threshold=0.99),
    )
    dod = engine.derive(request="any", context={CONTEXT_KEY_KIND: "k"})
    assert [c.name for c in dod.criteria] == ["must_be_present"]
    assert dod._provenance == {"lessons": ["must_be_present"]}
    assert dod.confidence == 0.4
    assert all(c.source == "lessons" for c in dod.criteria)
