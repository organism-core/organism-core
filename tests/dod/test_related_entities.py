"""Tests for ``RelatedEntitiesSource`` — prefix-cluster and
tag-overlap heuristics, each as its own source instance with a
distinct provenance bucket.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from organism.dod import (
    Criterion,
    DoD,
    DoDEngine,
    DoDEngineSettings,
    RelatedEntitiesSettings,
    RelatedEntitiesSource,
)
from organism.memory import Entity, EntityStore


# ---------- helpers


def _store(tmp_path: Path) -> EntityStore:
    return EntityStore(tmp_path / "entities")


def _seed(
    store: EntityStore,
    entity_id: str,
    *,
    criteria: list[dict] | None = None,
    tags: list[str] | None = None,
) -> None:
    fm: dict = {}
    if criteria is not None:
        fm["dod"] = {"criteria": criteria}
    if tags is not None:
        fm["tags"] = tags
    store.write(entity_id, Entity(frontmatter=fm, body=""))


# ============================================================
# Construction modes
# ============================================================


def test_class_level_name_is_canonical():
    assert RelatedEntitiesSource.name == "related_entities"


def test_default_instance_name_is_canonical():
    src = RelatedEntitiesSource()
    assert src.name == "related_entities"
    assert src.lookup_mode is None


def test_prefix_mode_name():
    src = RelatedEntitiesSource(
        lookup_mode=RelatedEntitiesSource.MODE_PREFIX
    )
    assert src.name == "related_entities:prefix"


def test_tags_mode_name():
    src = RelatedEntitiesSource(
        lookup_mode=RelatedEntitiesSource.MODE_TAGS
    )
    assert src.name == "related_entities:tags"


def test_rejects_unknown_mode():
    with pytest.raises(ValueError, match="unknown lookup_mode"):
        RelatedEntitiesSource(lookup_mode="bogus")


# ============================================================
# No-store / no-context behavior (stub semantics)
# ============================================================


def test_no_store_returns_empty():
    src = RelatedEntitiesSource()
    out = src.contribute(request="r", context={}, current=DoD())
    assert out.criteria == []
    assert out.evidence == {}


def test_no_entity_id_returns_empty(tmp_path: Path):
    src = RelatedEntitiesSource(store=_store(tmp_path))
    out = src.contribute(request="r", context={}, current=DoD())
    assert out.criteria == []
    assert out.evidence == {}


def test_unknown_entity_id_records_not_found(tmp_path: Path):
    src = RelatedEntitiesSource(store=_store(tmp_path))
    out = src.contribute(
        request="r",
        context={"entity_id": "ghost"},
        current=DoD(),
    )
    assert out.criteria == []
    assert out.evidence["found"] is False


# ============================================================
# Prefix-cluster heuristic
# ============================================================


def test_prefix_mode_finds_siblings_with_same_prefix(tmp_path: Path):
    s = _store(tmp_path)
    _seed(s, "343_alpha", criteria=[{"name": "scope_clear", "expected": True}])
    _seed(s, "343_beta", criteria=[{"name": "schedule_set", "expected": True}])
    _seed(s, "999_gamma", criteria=[{"name": "irrelevant", "expected": True}])

    src = RelatedEntitiesSource(
        store=s, lookup_mode=RelatedEntitiesSource.MODE_PREFIX
    )
    out = src.contribute(
        request="r",
        context={"entity_id": "343_alpha"},
        current=DoD(),
    )

    names = [c.name for c in out.criteria]
    assert "schedule_set" in names
    assert "irrelevant" not in names
    assert "343_beta" in out.evidence["related_ids"]
    assert "999_gamma" not in out.evidence["related_ids"]


def test_prefix_mode_skips_self(tmp_path: Path):
    s = _store(tmp_path)
    _seed(s, "343_alpha", criteria=[{"name": "self_c", "expected": True}])
    _seed(s, "343_beta", criteria=[{"name": "sib_c", "expected": True}])
    src = RelatedEntitiesSource(
        store=s, lookup_mode=RelatedEntitiesSource.MODE_PREFIX
    )
    out = src.contribute(
        request="r",
        context={"entity_id": "343_alpha"},
        current=DoD(),
    )
    assert "343_alpha" not in out.evidence["related_ids"]
    assert "self_c" not in [c.name for c in out.criteria]


def test_prefix_mode_no_separator_in_id_returns_empty(tmp_path: Path):
    s = _store(tmp_path)
    _seed(s, "alpha", criteria=[{"name": "c", "expected": True}])
    _seed(s, "alphabeta", criteria=[{"name": "x", "expected": True}])
    src = RelatedEntitiesSource(
        store=s, lookup_mode=RelatedEntitiesSource.MODE_PREFIX
    )
    out = src.contribute(
        request="r",
        context={"entity_id": "alpha"},
        current=DoD(),
    )
    assert out.criteria == []


def test_prefix_mode_custom_separator(tmp_path: Path):
    s = _store(tmp_path)
    _seed(s, "343-alpha", criteria=[{"name": "c1", "expected": True}])
    _seed(s, "343-beta", criteria=[{"name": "c2", "expected": True}])
    src = RelatedEntitiesSource(
        store=s,
        lookup_mode=RelatedEntitiesSource.MODE_PREFIX,
        settings=RelatedEntitiesSettings(prefix_separator="-"),
    )
    out = src.contribute(
        request="r",
        context={"entity_id": "343-alpha"},
        current=DoD(),
    )
    assert [c.name for c in out.criteria] == ["c2"]


# ============================================================
# Tag-overlap heuristic
# ============================================================


def test_tags_mode_finds_siblings_with_overlapping_tags(tmp_path: Path):
    s = _store(tmp_path)
    _seed(
        s,
        "alpha",
        tags=["foo", "bar"],
        criteria=[{"name": "alpha_c", "expected": True}],
    )
    _seed(
        s,
        "beta",
        tags=["foo", "baz"],
        criteria=[{"name": "beta_c", "expected": True}],
    )
    _seed(
        s,
        "gamma",
        tags=["nothing"],
        criteria=[{"name": "gamma_c", "expected": True}],
    )
    src = RelatedEntitiesSource(
        store=s, lookup_mode=RelatedEntitiesSource.MODE_TAGS
    )
    out = src.contribute(
        request="r",
        context={"entity_id": "alpha"},
        current=DoD(),
    )
    assert "beta_c" in [c.name for c in out.criteria]
    assert "gamma_c" not in [c.name for c in out.criteria]


def test_tags_mode_min_overlap_setting(tmp_path: Path):
    s = _store(tmp_path)
    _seed(
        s,
        "alpha",
        tags=["foo", "bar", "baz"],
        criteria=[{"name": "alpha_c", "expected": True}],
    )
    _seed(
        s,
        "beta",
        tags=["foo"],
        criteria=[{"name": "beta_c", "expected": True}],
    )
    _seed(
        s,
        "gamma",
        tags=["foo", "bar"],
        criteria=[{"name": "gamma_c", "expected": True}],
    )

    # With min_overlap=2, only gamma qualifies
    src = RelatedEntitiesSource(
        store=s,
        lookup_mode=RelatedEntitiesSource.MODE_TAGS,
        settings=RelatedEntitiesSettings(tags_min_overlap=2),
    )
    out = src.contribute(
        request="r",
        context={"entity_id": "alpha"},
        current=DoD(),
    )
    names = [c.name for c in out.criteria]
    assert "gamma_c" in names
    assert "beta_c" not in names


def test_tags_mode_no_tags_on_focal_returns_empty(tmp_path: Path):
    s = _store(tmp_path)
    _seed(s, "alpha", criteria=[{"name": "c", "expected": True}])  # no tags
    _seed(
        s,
        "beta",
        tags=["foo"],
        criteria=[{"name": "beta_c", "expected": True}],
    )
    src = RelatedEntitiesSource(
        store=s, lookup_mode=RelatedEntitiesSource.MODE_TAGS
    )
    out = src.contribute(
        request="r",
        context={"entity_id": "alpha"},
        current=DoD(),
    )
    assert out.criteria == []


def test_tags_mode_custom_frontmatter_key(tmp_path: Path):
    s = _store(tmp_path)
    s.write(
        "alpha",
        Entity(
            frontmatter={"labels": ["foo"], "dod": {"criteria": []}},
            body="",
        ),
    )
    s.write(
        "beta",
        Entity(
            frontmatter={
                "labels": ["foo"],
                "dod": {"criteria": [{"name": "beta_c", "expected": True}]},
            },
            body="",
        ),
    )
    src = RelatedEntitiesSource(
        store=s,
        lookup_mode=RelatedEntitiesSource.MODE_TAGS,
        settings=RelatedEntitiesSettings(tags_frontmatter_key="labels"),
    )
    out = src.contribute(
        request="r",
        context={"entity_id": "alpha"},
        current=DoD(),
    )
    assert [c.name for c in out.criteria] == ["beta_c"]


# ============================================================
# Cross-entity weight factor
# ============================================================


def test_criteria_weight_is_scaled_by_cross_entity_factor(tmp_path: Path):
    s = _store(tmp_path)
    _seed(s, "343_alpha", criteria=[])
    _seed(
        s,
        "343_beta",
        criteria=[
            {"name": "sib_c", "expected": True, "weight": 2.0},
        ],
    )
    src = RelatedEntitiesSource(
        store=s,
        lookup_mode=RelatedEntitiesSource.MODE_PREFIX,
        settings=RelatedEntitiesSettings(cross_entity_weight_factor=0.5),
    )
    out = src.contribute(
        request="r",
        context={"entity_id": "343_alpha"},
        current=DoD(),
    )
    [c] = out.criteria
    assert c.weight == pytest.approx(1.0)  # 2.0 * 0.5


# ============================================================
# Dedup against current DoD
# ============================================================


def test_skips_criteria_already_present_in_current(tmp_path: Path):
    s = _store(tmp_path)
    _seed(s, "343_alpha", criteria=[])
    _seed(
        s,
        "343_beta",
        criteria=[
            {"name": "dupe", "expected": True},
            {"name": "fresh", "expected": True},
        ],
    )
    src = RelatedEntitiesSource(
        store=s, lookup_mode=RelatedEntitiesSource.MODE_PREFIX
    )
    current = DoD(criteria=[Criterion(name="dupe", expected=True)])
    out = src.contribute(
        request="r",
        context={"entity_id": "343_alpha"},
        current=current,
    )
    assert [c.name for c in out.criteria] == ["fresh"]


# ============================================================
# Confidence
# ============================================================


def test_confidence_capped_at_max(tmp_path: Path):
    """20 siblings × 0.05 each would be 1.0 — cap at default max 0.3."""
    s = _store(tmp_path)
    _seed(s, "343_alpha", criteria=[])
    for i in range(20):
        _seed(
            s,
            f"343_sib{i:02d}",
            criteria=[{"name": f"c{i}", "expected": True}],
        )
    src = RelatedEntitiesSource(
        store=s, lookup_mode=RelatedEntitiesSource.MODE_PREFIX
    )
    out = src.contribute(
        request="r",
        context={"entity_id": "343_alpha"},
        current=DoD(),
    )
    assert out.confidence_delta <= 0.3


def test_max_related_caps_iteration(tmp_path: Path):
    s = _store(tmp_path)
    _seed(s, "343_alpha", criteria=[])
    for i in range(5):
        _seed(
            s,
            f"343_sib{i}",
            criteria=[{"name": f"c{i}", "expected": True}],
        )
    src = RelatedEntitiesSource(
        store=s,
        lookup_mode=RelatedEntitiesSource.MODE_PREFIX,
        settings=RelatedEntitiesSettings(max_related=2),
    )
    out = src.contribute(
        request="r",
        context={"entity_id": "343_alpha"},
        current=DoD(),
    )
    assert len(out.evidence["related_ids"]) == 2


# ============================================================
# Engine integration — separate provenance buckets
# ============================================================


def test_engine_writes_separate_provenance_buckets(tmp_path: Path):
    s = _store(tmp_path)
    _seed(s, "343_alpha", tags=["foo"], criteria=[])
    _seed(
        s,
        "343_beta",
        criteria=[{"name": "prefix_c", "expected": True}],
    )
    _seed(
        s,
        "999_zeta",
        tags=["foo"],
        criteria=[{"name": "tag_c", "expected": True}],
    )

    engine = DoDEngine(
        sources=[
            RelatedEntitiesSource(
                store=s, lookup_mode=RelatedEntitiesSource.MODE_PREFIX
            ),
            RelatedEntitiesSource(
                store=s, lookup_mode=RelatedEntitiesSource.MODE_TAGS
            ),
        ],
        settings=DoDEngineSettings(threshold=1.0),
    )
    dod = engine.derive(
        request="r", context={"entity_id": "343_alpha"}
    )

    assert "related_entities:prefix" in dod._provenance
    assert "related_entities:tags" in dod._provenance
    assert "related_entities" not in dod._provenance
    assert dod._provenance["related_entities:prefix"] == ["prefix_c"]
    assert dod._provenance["related_entities:tags"] == ["tag_c"]


def test_engine_dedups_overlapping_criteria_between_modes(tmp_path: Path):
    """If prefix and tags both surface the same criterion-name, only
    the first source-list entry wins (engine sees `current` already
    populated when the second source runs)."""
    s = _store(tmp_path)
    _seed(s, "343_alpha", tags=["foo"], criteria=[])
    _seed(
        s,
        "343_beta",
        tags=["foo"],
        criteria=[{"name": "shared", "expected": True}],
    )

    engine = DoDEngine(
        sources=[
            RelatedEntitiesSource(
                store=s, lookup_mode=RelatedEntitiesSource.MODE_PREFIX
            ),
            RelatedEntitiesSource(
                store=s, lookup_mode=RelatedEntitiesSource.MODE_TAGS
            ),
        ],
        settings=DoDEngineSettings(threshold=1.0),
    )
    dod = engine.derive(
        request="r", context={"entity_id": "343_alpha"}
    )
    # "shared" appears only once.
    names = [c.name for c in dod.criteria]
    assert names.count("shared") == 1
    # First source (prefix) gets the provenance entry.
    assert dod._provenance["related_entities:prefix"] == ["shared"]
    assert dod._provenance.get("related_entities:tags") == []


# ============================================================
# lookup_mode=None — combined bucket
# ============================================================


def test_lookup_mode_none_unions_both_heuristics(tmp_path: Path):
    s = _store(tmp_path)
    _seed(s, "343_alpha", tags=["foo"], criteria=[])
    _seed(
        s,
        "343_beta",
        criteria=[{"name": "prefix_c", "expected": True}],
    )
    _seed(
        s,
        "999_zeta",
        tags=["foo"],
        criteria=[{"name": "tag_c", "expected": True}],
    )
    src = RelatedEntitiesSource(store=s)  # lookup_mode=None
    out = src.contribute(
        request="r",
        context={"entity_id": "343_alpha"},
        current=DoD(),
    )
    names = {c.name for c in out.criteria}
    assert names == {"prefix_c", "tag_c"}
