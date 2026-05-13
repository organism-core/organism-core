"""Tests for ``PatternRegistry`` and ``DomainPatternSource``.

The source ships in two parallel instances (``lookup_mode="tuple"``
and ``lookup_mode="action_only"``) so the engine emits separate
provenance buckets — that lineage signal is the whole reason for the
two-instance pattern, and these tests pin it down.
"""

from __future__ import annotations

from typing import Any

import pytest

from organism.dod import (
    Criterion,
    DoD,
    DoDEngine,
    DoDEngineSettings,
    DomainPatternSettings,
    DomainPatternSource,
    PatternRegistry,
    SourceContribution,
)


# ============================================================
# PatternRegistry — pure data structure
# ============================================================


def test_registry_starts_empty():
    r = PatternRegistry()
    assert len(r) == 0
    assert r.keys() == []


def test_registry_register_and_lookup_tuple_key():
    r = PatternRegistry()
    r.register(
        action_type="review",
        entity_type="project",
        criteria=[Criterion(name="has_scope", expected=True)],
    )
    hits = r.lookup(action_type="review", entity_type="project")
    assert len(hits) == 1
    assert hits[0].name == "has_scope"


def test_registry_register_and_lookup_action_only_key():
    r = PatternRegistry()
    r.register(
        action_type="review",
        criteria=[Criterion(name="reviewer_assigned", expected=True)],
    )
    hits = r.lookup(action_type="review")
    assert [c.name for c in hits] == ["reviewer_assigned"]


def test_registry_tuple_and_action_only_keys_are_separate():
    """``entity_type=None`` is a distinct key from any concrete entity_type."""
    r = PatternRegistry()
    r.register(
        action_type="review",
        entity_type="project",
        criteria=[Criterion(name="tuple_c", expected=True)],
    )
    r.register(
        action_type="review",
        criteria=[Criterion(name="action_only_c", expected=True)],
    )
    tuple_hits = r.lookup(action_type="review", entity_type="project")
    action_only_hits = r.lookup(action_type="review")
    assert [c.name for c in tuple_hits] == ["tuple_c"]
    assert [c.name for c in action_only_hits] == ["action_only_c"]


def test_registry_lookup_unknown_returns_empty_list():
    r = PatternRegistry()
    assert r.lookup(action_type="nope") == []
    assert r.lookup(action_type="nope", entity_type="also_nope") == []


def test_registry_register_appends_on_duplicate_key():
    r = PatternRegistry()
    r.register(
        action_type="review",
        criteria=[Criterion(name="a", expected=True)],
    )
    r.register(
        action_type="review",
        criteria=[Criterion(name="b", expected=True)],
    )
    hits = r.lookup(action_type="review")
    assert [c.name for c in hits] == ["a", "b"]


def test_registry_lookup_returns_copy_not_internal_list():
    r = PatternRegistry()
    r.register(
        action_type="review",
        criteria=[Criterion(name="a", expected=True)],
    )
    hits = r.lookup(action_type="review")
    hits.append(Criterion(name="injected", expected=True))
    second = r.lookup(action_type="review")
    assert [c.name for c in second] == ["a"]


def test_registry_clear_empties_storage():
    r = PatternRegistry()
    r.register(
        action_type="review",
        criteria=[Criterion(name="a", expected=True)],
    )
    r.clear()
    assert len(r) == 0
    assert r.lookup(action_type="review") == []


def test_registry_rejects_empty_action_type():
    r = PatternRegistry()
    with pytest.raises(ValueError):
        r.register(action_type="", criteria=[])


def test_registry_rejects_non_criterion_entries():
    r = PatternRegistry()
    with pytest.raises(TypeError):
        r.register(
            action_type="review",
            criteria=[{"name": "fake", "expected": True}],  # type: ignore[list-item]
        )


def test_registry_len_counts_criteria_not_keys():
    r = PatternRegistry()
    r.register(
        action_type="a",
        criteria=[
            Criterion(name="c1", expected=True),
            Criterion(name="c2", expected=True),
        ],
    )
    r.register(
        action_type="b",
        criteria=[Criterion(name="c3", expected=True)],
    )
    assert len(r) == 3


# ============================================================
# DomainPatternSource — construction modes
# ============================================================


def test_source_class_level_name_is_canonical():
    """Stub tests read ``cls.name`` — must stay 'domain_pattern'."""
    assert DomainPatternSource.name == "domain_pattern"


def test_source_default_instance_name_is_canonical():
    src = DomainPatternSource()
    assert src.name == "domain_pattern"
    assert src.lookup_mode is None


def test_source_tuple_mode_instance_name():
    src = DomainPatternSource(
        lookup_mode=DomainPatternSource.MODE_TUPLE
    )
    assert src.name == "domain_pattern:tuple"


def test_source_action_only_mode_instance_name():
    src = DomainPatternSource(
        lookup_mode=DomainPatternSource.MODE_ACTION_ONLY
    )
    assert src.name == "domain_pattern:action_only"


def test_source_rejects_unknown_mode():
    with pytest.raises(ValueError, match="unknown lookup_mode"):
        DomainPatternSource(lookup_mode="bogus")


# ============================================================
# DomainPatternSource — no-registry behavior (stub semantics)
# ============================================================


def test_source_no_registry_returns_empty():
    src = DomainPatternSource()
    out = src.contribute(request="r", context={}, current=DoD())
    assert out.criteria == []
    assert out.evidence == {}
    assert out.confidence_delta == 0.0


def test_source_no_action_type_returns_empty():
    r = PatternRegistry()
    r.register(
        action_type="review",
        criteria=[Criterion(name="c", expected=True)],
    )
    src = DomainPatternSource(registry=r)
    out = src.contribute(request="r", context={}, current=DoD())
    assert out.criteria == []


def test_source_tuple_mode_without_entity_type_returns_empty():
    r = PatternRegistry()
    r.register(
        action_type="review",
        entity_type="project",
        criteria=[Criterion(name="c", expected=True)],
    )
    src = DomainPatternSource(
        registry=r, lookup_mode=DomainPatternSource.MODE_TUPLE
    )
    out = src.contribute(
        request="r",
        context={"action_type": "review"},  # no entity_type
        current=DoD(),
    )
    assert out.criteria == []


# ============================================================
# DomainPatternSource — tuple mode
# ============================================================


def test_tuple_mode_returns_criteria_for_matching_pair():
    r = PatternRegistry()
    r.register(
        action_type="review",
        entity_type="project",
        criteria=[
            Criterion(name="has_scope", expected=True),
            Criterion(name="approver_set", expected=True),
        ],
    )
    src = DomainPatternSource(
        registry=r, lookup_mode=DomainPatternSource.MODE_TUPLE
    )
    out = src.contribute(
        request="r",
        context={"action_type": "review", "entity_type": "project"},
        current=DoD(),
    )
    assert [c.name for c in out.criteria] == ["has_scope", "approver_set"]
    assert out.confidence_delta > 0.0
    assert out.evidence["action_type"] == "review"
    assert out.evidence["entity_type"] == "project"
    assert out.evidence["patterns_found"] == 2


def test_tuple_mode_ignores_action_only_patterns():
    r = PatternRegistry()
    r.register(
        action_type="review",
        criteria=[Criterion(name="action_only_c", expected=True)],
    )
    src = DomainPatternSource(
        registry=r, lookup_mode=DomainPatternSource.MODE_TUPLE
    )
    out = src.contribute(
        request="r",
        context={"action_type": "review", "entity_type": "project"},
        current=DoD(),
    )
    assert out.criteria == []


def test_tuple_mode_no_match_carries_zero_count_evidence():
    r = PatternRegistry()
    r.register(
        action_type="other",
        entity_type="project",
        criteria=[Criterion(name="x", expected=True)],
    )
    src = DomainPatternSource(
        registry=r, lookup_mode=DomainPatternSource.MODE_TUPLE
    )
    out = src.contribute(
        request="r",
        context={"action_type": "review", "entity_type": "project"},
        current=DoD(),
    )
    assert out.criteria == []
    assert out.evidence["patterns_found"] == 0


# ============================================================
# DomainPatternSource — action_only mode
# ============================================================


def test_action_only_mode_returns_action_only_patterns():
    r = PatternRegistry()
    r.register(
        action_type="review",
        criteria=[Criterion(name="reviewer_assigned", expected=True)],
    )
    src = DomainPatternSource(
        registry=r, lookup_mode=DomainPatternSource.MODE_ACTION_ONLY
    )
    out = src.contribute(
        request="r",
        context={"action_type": "review", "entity_type": "project"},
        current=DoD(),
    )
    assert [c.name for c in out.criteria] == ["reviewer_assigned"]
    assert out.evidence["entity_type"] is None


def test_action_only_mode_ignores_tuple_patterns():
    r = PatternRegistry()
    r.register(
        action_type="review",
        entity_type="project",
        criteria=[Criterion(name="tuple_c", expected=True)],
    )
    src = DomainPatternSource(
        registry=r, lookup_mode=DomainPatternSource.MODE_ACTION_ONLY
    )
    out = src.contribute(
        request="r",
        context={"action_type": "review", "entity_type": "project"},
        current=DoD(),
    )
    assert out.criteria == []


def test_action_only_mode_runs_without_entity_type_in_context():
    r = PatternRegistry()
    r.register(
        action_type="review",
        criteria=[Criterion(name="c", expected=True)],
    )
    src = DomainPatternSource(
        registry=r, lookup_mode=DomainPatternSource.MODE_ACTION_ONLY
    )
    out = src.contribute(
        request="r",
        context={"action_type": "review"},
        current=DoD(),
    )
    assert [c.name for c in out.criteria] == ["c"]


# ============================================================
# DomainPatternSource — confidence cap
# ============================================================


def test_confidence_capped_at_max_delta():
    r = PatternRegistry()
    # 20 patterns × 0.15 per pattern would be 3.0 — cap at max (0.4)
    r.register(
        action_type="review",
        criteria=[
            Criterion(name=f"c{i}", expected=True) for i in range(20)
        ],
    )
    src = DomainPatternSource(
        registry=r, lookup_mode=DomainPatternSource.MODE_ACTION_ONLY
    )
    out = src.contribute(
        request="r",
        context={"action_type": "review"},
        current=DoD(),
    )
    assert out.confidence_delta == 0.4
    assert len(out.criteria) == 20


def test_confidence_scales_with_pattern_count():
    r = PatternRegistry()
    r.register(
        action_type="review",
        criteria=[
            Criterion(name="a", expected=True),
            Criterion(name="b", expected=True),
        ],
    )
    src = DomainPatternSource(
        registry=r,
        lookup_mode=DomainPatternSource.MODE_ACTION_ONLY,
        settings=DomainPatternSettings(
            confidence_per_pattern=0.1, max_confidence_delta=1.0
        ),
    )
    out = src.contribute(
        request="r",
        context={"action_type": "review"},
        current=DoD(),
    )
    assert out.confidence_delta == pytest.approx(0.2)


# ============================================================
# DomainPatternSource — current-dedup
# ============================================================


def test_skips_criteria_already_present_in_current():
    r = PatternRegistry()
    r.register(
        action_type="review",
        criteria=[
            Criterion(name="dupe", expected=True),
            Criterion(name="fresh", expected=True),
        ],
    )
    src = DomainPatternSource(
        registry=r, lookup_mode=DomainPatternSource.MODE_ACTION_ONLY
    )
    current = DoD(criteria=[Criterion(name="dupe", expected=True)])
    out = src.contribute(
        request="r",
        context={"action_type": "review"},
        current=current,
    )
    assert [c.name for c in out.criteria] == ["fresh"]


# ============================================================
# Two-instance pattern — engine integration
# ============================================================


def test_engine_writes_separate_provenance_buckets_for_two_modes():
    """The whole point of the two-instance pattern: tuple and
    action_only criteria land in distinct provenance buckets."""
    r = PatternRegistry()
    r.register(
        action_type="review",
        entity_type="project",
        criteria=[Criterion(name="tuple_c", expected=True)],
    )
    r.register(
        action_type="review",
        criteria=[Criterion(name="action_only_c", expected=True)],
    )

    engine = DoDEngine(
        sources=[
            DomainPatternSource(
                registry=r,
                lookup_mode=DomainPatternSource.MODE_TUPLE,
            ),
            DomainPatternSource(
                registry=r,
                lookup_mode=DomainPatternSource.MODE_ACTION_ONLY,
            ),
        ],
        settings=DoDEngineSettings(threshold=1.0),
    )
    dod = engine.derive(
        request="r",
        context={"action_type": "review", "entity_type": "project"},
    )

    assert "domain_pattern:tuple" in dod._provenance
    assert "domain_pattern:action_only" in dod._provenance
    assert "domain_pattern" not in dod._provenance
    assert dod._provenance["domain_pattern:tuple"] == ["tuple_c"]
    assert dod._provenance["domain_pattern:action_only"] == ["action_only_c"]


def test_engine_stamps_criterion_source_with_mode_specific_name():
    r = PatternRegistry()
    r.register(
        action_type="review",
        entity_type="project",
        criteria=[Criterion(name="tuple_c", expected=True)],
    )
    engine = DoDEngine(
        sources=[
            DomainPatternSource(
                registry=r,
                lookup_mode=DomainPatternSource.MODE_TUPLE,
            ),
        ],
        settings=DoDEngineSettings(threshold=1.0),
    )
    dod = engine.derive(
        request="r",
        context={"action_type": "review", "entity_type": "project"},
    )
    [c] = dod.criteria
    assert c.source == "domain_pattern:tuple"


# ============================================================
# Lookup-mode None — combined-bucket fallback
# ============================================================


def test_lookup_mode_none_combines_both_buckets():
    r = PatternRegistry()
    r.register(
        action_type="review",
        entity_type="project",
        criteria=[Criterion(name="tuple_c", expected=True)],
    )
    r.register(
        action_type="review",
        criteria=[Criterion(name="action_only_c", expected=True)],
    )
    src = DomainPatternSource(registry=r)  # lookup_mode=None
    out = src.contribute(
        request="r",
        context={"action_type": "review", "entity_type": "project"},
        current=DoD(),
    )
    names = {c.name for c in out.criteria}
    assert names == {"tuple_c", "action_only_c"}


def test_lookup_mode_none_dedupes_overlapping_names():
    r = PatternRegistry()
    r.register(
        action_type="review",
        entity_type="project",
        criteria=[Criterion(name="shared", expected=True)],
    )
    r.register(
        action_type="review",
        criteria=[Criterion(name="shared", expected=True)],
    )
    src = DomainPatternSource(registry=r)
    out = src.contribute(
        request="r",
        context={"action_type": "review", "entity_type": "project"},
        current=DoD(),
    )
    assert len(out.criteria) == 1
    assert out.criteria[0].name == "shared"
