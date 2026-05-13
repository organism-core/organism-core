from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from organism.dod import Criterion
from organism.lessons import (
    LessonsAggregator,
    LessonsAggregatorSettings,
    LessonsStore,
)
from organism.provenance import Provenance


def _make_aggregator(
    tmp_path: Path,
    **settings_kwargs,
) -> LessonsAggregator:
    store = LessonsStore(tmp_path)
    settings = (
        LessonsAggregatorSettings(**settings_kwargs)
        if settings_kwargs
        else None
    )
    return LessonsAggregator(store=store, settings=settings)


def test_record_lesson_creates_persisted_lesson(tmp_path: Path):
    agg = _make_aggregator(tmp_path)
    lesson = agg.record_lesson(
        kind="k",
        observation="hello",
    )
    assert lesson.id
    assert lesson.kind == "k"
    assert agg.store.exists(lesson.id)


def test_record_lesson_with_full_args(tmp_path: Path):
    agg = _make_aggregator(tmp_path)
    crit = Criterion(name="x", expected=1)
    prov = Provenance(
        author="user_a",
        timestamp=datetime(2026, 5, 9, tzinfo=timezone.utc),
    )
    lesson = agg.record_lesson(
        kind="k",
        observation="rule",
        criteria_hint=[crit],
        confidence_delta=0.2,
        context_pattern={"entity_type": "x"},
        provenance=prov,
    )
    assert lesson.criteria_hint[0].name == "x"
    assert lesson.confidence_delta == 0.2
    assert lesson.context_pattern == {"entity_type": "x"}
    assert lesson.provenance.author == "user_a"


def test_record_lesson_unique_ids(tmp_path: Path):
    agg = _make_aggregator(tmp_path)
    l1 = agg.record_lesson(kind="k", observation="a")
    l2 = agg.record_lesson(kind="k", observation="b")
    assert l1.id != l2.id


def test_query_filters_by_kind(tmp_path: Path):
    agg = _make_aggregator(tmp_path)
    l1 = agg.record_lesson(kind="ka", observation="a")
    agg.record_lesson(kind="kb", observation="b")
    results = agg.query_for_request("ka", context={})
    assert {l.id for l in results} == {l1.id}


def test_query_empty_pattern_matches_any_context(tmp_path: Path):
    agg = _make_aggregator(tmp_path)
    l1 = agg.record_lesson(kind="k", observation="catchall")
    results = agg.query_for_request(
        "k", context={"any_key": "any_value"}
    )
    assert [l.id for l in results] == [l1.id]


def test_query_pattern_must_match_all_keys(tmp_path: Path):
    agg = _make_aggregator(tmp_path)
    l1 = agg.record_lesson(
        kind="k",
        observation="match",
        context_pattern={"entity_type": "wohnbau", "geschoss": "UG"},
    )
    matched = agg.query_for_request(
        "k", context={"entity_type": "wohnbau", "geschoss": "UG"}
    )
    assert [l.id for l in matched] == [l1.id]
    not_matched = agg.query_for_request(
        "k", context={"entity_type": "wohnbau", "geschoss": "EG"}
    )
    assert not_matched == []


def test_query_missing_context_key_fails_match(tmp_path: Path):
    agg = _make_aggregator(tmp_path)
    agg.record_lesson(
        kind="k",
        observation="match",
        context_pattern={"required_key": "value"},
    )
    results = agg.query_for_request("k", context={})
    assert results == []


def test_query_returns_newest_first(tmp_path: Path):
    import time

    agg = _make_aggregator(tmp_path)
    agg.record_lesson(kind="k", observation="first")
    time.sleep(0.02)  # Windows 15ms clock resolution — disambiguate timestamps
    agg.record_lesson(kind="k", observation="second")
    time.sleep(0.02)
    agg.record_lesson(kind="k", observation="third")
    results = agg.query_for_request("k", context={})
    assert [l.observation for l in results] == ["third", "second", "first"]


def test_query_respects_max_results(tmp_path: Path):
    agg = _make_aggregator(tmp_path, query_max_results=2)
    for i in range(5):
        agg.record_lesson(kind="k", observation=f"obs{i}")
    results = agg.query_for_request("k", context={})
    assert len(results) == 2


def test_query_explicit_max_results_override(tmp_path: Path):
    agg = _make_aggregator(tmp_path, query_max_results=10)
    for i in range(5):
        agg.record_lesson(kind="k", observation=f"obs{i}")
    results = agg.query_for_request("k", context={}, max_results=2)
    assert len(results) == 2


def test_query_unknown_kind_returns_empty(tmp_path: Path):
    agg = _make_aggregator(tmp_path)
    agg.record_lesson(kind="real", observation="o")
    assert agg.query_for_request("ghost", context={}) == []
