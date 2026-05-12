from pathlib import Path

import pytest

from organism.dod import (
    DoD,
    DoDEngine,
    DoDEngineSettings,
    DoDSource,
    EntityFrontmatterSettings,
    EntityFrontmatterSource,
    UserClarificationSource,
)
from organism.dod.sources.entity_frontmatter import CONTEXT_KEY_ENTITY_ID
from organism.memory import Entity, EntityStore


def _make_store(tmp_path: Path) -> EntityStore:
    return EntityStore(tmp_path)


def test_satisfies_protocol(tmp_path: Path):
    source = EntityFrontmatterSource(store=_make_store(tmp_path))
    assert isinstance(source, DoDSource)


def test_no_entity_id_in_context_yields_silent_contribution(tmp_path: Path):
    source = EntityFrontmatterSource(store=_make_store(tmp_path))
    contribution = source.contribute(
        request="any", context={}, current=DoD()
    )
    assert contribution.criteria == []
    assert contribution.confidence_delta == 0.0
    assert contribution.evidence == {}


def test_entity_id_present_but_entity_missing(tmp_path: Path):
    source = EntityFrontmatterSource(store=_make_store(tmp_path))
    contribution = source.contribute(
        request="any",
        context={CONTEXT_KEY_ENTITY_ID: "ghost"},
        current=DoD(),
    )
    assert contribution.criteria == []
    assert contribution.confidence_delta == 0.0
    assert contribution.evidence == {"entity_id": "ghost", "found": False}


def test_entity_without_dod_block(tmp_path: Path):
    store = _make_store(tmp_path)
    store.write("alpha", Entity(frontmatter={"name": "Alpha"}, body=""))

    source = EntityFrontmatterSource(store=store)
    contribution = source.contribute(
        request="any",
        context={CONTEXT_KEY_ENTITY_ID: "alpha"},
        current=DoD(),
    )
    assert contribution.criteria == []
    assert contribution.confidence_delta == 0.0
    assert contribution.evidence == {
        "entity_id": "alpha",
        "found": True,
        "criteria_count": 0,
    }


def test_entity_with_one_criterion(tmp_path: Path):
    store = _make_store(tmp_path)
    store.write(
        "alpha",
        Entity(
            frontmatter={
                "dod": {
                    "criteria": [
                        {"name": "must_have_id", "expected": True}
                    ]
                }
            },
            body="",
        ),
    )

    source = EntityFrontmatterSource(store=store)
    contribution = source.contribute(
        request="any",
        context={CONTEXT_KEY_ENTITY_ID: "alpha"},
        current=DoD(),
    )
    assert len(contribution.criteria) == 1
    c = contribution.criteria[0]
    assert c.name == "must_have_id"
    assert c.expected is True
    assert c.weight == 1.0
    assert contribution.evidence["criteria_count"] == 1


def test_entity_with_multiple_criteria_preserves_order_and_weights(
    tmp_path: Path,
):
    store = _make_store(tmp_path)
    store.write(
        "alpha",
        Entity(
            frontmatter={
                "dod": {
                    "criteria": [
                        {"name": "first", "expected": 1},
                        {"name": "second", "expected": 2, "weight": 0.5},
                        {"name": "third", "expected": 3, "weight": 2.0},
                    ]
                }
            },
            body="",
        ),
    )

    source = EntityFrontmatterSource(store=store)
    contribution = source.contribute(
        request="any",
        context={CONTEXT_KEY_ENTITY_ID: "alpha"},
        current=DoD(),
    )
    names = [c.name for c in contribution.criteria]
    weights = [c.weight for c in contribution.criteria]
    assert names == ["first", "second", "third"]
    assert weights == [1.0, 0.5, 2.0]


def test_confidence_when_criteria_present(tmp_path: Path):
    store = _make_store(tmp_path)
    store.write(
        "alpha",
        Entity(
            frontmatter={
                "dod": {"criteria": [{"name": "x", "expected": 1}]}
            },
            body="",
        ),
    )
    source = EntityFrontmatterSource(
        store=store,
        settings=EntityFrontmatterSettings(confidence_when_loaded=0.7),
    )
    contribution = source.contribute(
        request="any",
        context={CONTEXT_KEY_ENTITY_ID: "alpha"},
        current=DoD(),
    )
    assert contribution.confidence_delta == 0.7


def test_zero_confidence_when_dod_block_missing(tmp_path: Path):
    store = _make_store(tmp_path)
    store.write(
        "alpha", Entity(frontmatter={"name": "Alpha"}, body="")
    )
    source = EntityFrontmatterSource(
        store=store,
        settings=EntityFrontmatterSettings(confidence_when_loaded=0.7),
    )
    contribution = source.contribute(
        request="any",
        context={CONTEXT_KEY_ENTITY_ID: "alpha"},
        current=DoD(),
    )
    assert contribution.confidence_delta == 0.0


def test_zero_confidence_when_criteria_list_empty(tmp_path: Path):
    store = _make_store(tmp_path)
    store.write(
        "alpha",
        Entity(frontmatter={"dod": {"criteria": []}}, body=""),
    )
    source = EntityFrontmatterSource(
        store=store,
        settings=EntityFrontmatterSettings(confidence_when_loaded=0.7),
    )
    contribution = source.contribute(
        request="any",
        context={CONTEXT_KEY_ENTITY_ID: "alpha"},
        current=DoD(),
    )
    assert contribution.confidence_delta == 0.0


def test_criterion_missing_name_raises(tmp_path: Path):
    store = _make_store(tmp_path)
    store.write(
        "alpha",
        Entity(
            frontmatter={"dod": {"criteria": [{"expected": True}]}},
            body="",
        ),
    )
    source = EntityFrontmatterSource(store=store)
    with pytest.raises(ValueError, match="missing required 'name'"):
        source.contribute(
            request="any",
            context={CONTEXT_KEY_ENTITY_ID: "alpha"},
            current=DoD(),
        )


def test_criterion_missing_expected_raises(tmp_path: Path):
    store = _make_store(tmp_path)
    store.write(
        "alpha",
        Entity(
            frontmatter={"dod": {"criteria": [{"name": "x"}]}},
            body="",
        ),
    )
    source = EntityFrontmatterSource(store=store)
    with pytest.raises(ValueError, match="missing required 'expected'"):
        source.contribute(
            request="any",
            context={CONTEXT_KEY_ENTITY_ID: "alpha"},
            current=DoD(),
        )


def test_criterion_not_a_mapping_raises(tmp_path: Path):
    store = _make_store(tmp_path)
    store.write(
        "alpha",
        Entity(
            frontmatter={"dod": {"criteria": ["not_a_dict"]}},
            body="",
        ),
    )
    source = EntityFrontmatterSource(store=store)
    with pytest.raises(ValueError, match="must be a mapping"):
        source.contribute(
            request="any",
            context={CONTEXT_KEY_ENTITY_ID: "alpha"},
            current=DoD(),
        )


def test_dod_block_not_a_mapping_raises(tmp_path: Path):
    store = _make_store(tmp_path)
    store.write(
        "alpha", Entity(frontmatter={"dod": "not_a_dict"}, body="")
    )
    source = EntityFrontmatterSource(store=store)
    with pytest.raises(ValueError, match="'dod' must be a mapping"):
        source.contribute(
            request="any",
            context={CONTEXT_KEY_ENTITY_ID: "alpha"},
            current=DoD(),
        )


def test_criteria_list_not_a_list_raises(tmp_path: Path):
    store = _make_store(tmp_path)
    store.write(
        "alpha",
        Entity(
            frontmatter={"dod": {"criteria": "not_a_list"}}, body=""
        ),
    )
    source = EntityFrontmatterSource(store=store)
    with pytest.raises(ValueError, match="'dod.criteria' must be a list"):
        source.contribute(
            request="any",
            context={CONTEXT_KEY_ENTITY_ID: "alpha"},
            current=DoD(),
        )


def test_engine_integration_single_source(tmp_path: Path):
    store = _make_store(tmp_path)
    store.write(
        "task_42",
        Entity(
            frontmatter={
                "dod": {
                    "criteria": [
                        {"name": "approved", "expected": True},
                        {"name": "validated", "expected": True, "weight": 0.5},
                    ]
                }
            },
            body="# Task 42",
        ),
    )

    engine = DoDEngine(
        sources=[
            EntityFrontmatterSource(
                store=store,
                settings=EntityFrontmatterSettings(confidence_when_loaded=0.6),
            )
        ],
        settings=DoDEngineSettings(threshold=0.5),
    )
    dod = engine.derive(
        request="execute", context={CONTEXT_KEY_ENTITY_ID: "task_42"}
    )

    assert [c.name for c in dod.criteria] == ["approved", "validated"]
    assert all(c.source == "entity_frontmatter" for c in dod.criteria)
    assert dod.confidence == 0.6
    assert dod.clarification_needed == []
    assert dod._provenance == {
        "entity_frontmatter": ["approved", "validated"]
    }


def test_engine_integration_entity_then_user_clarification(tmp_path: Path):
    store = _make_store(tmp_path)
    store.write(
        "task_42",
        Entity(
            frontmatter={
                "dod": {"criteria": [{"name": "x", "expected": 1}]}
            },
            body="",
        ),
    )

    engine = DoDEngine(
        sources=[
            EntityFrontmatterSource(
                store=store,
                settings=EntityFrontmatterSettings(confidence_when_loaded=0.3),
            ),
            UserClarificationSource(),
        ],
        settings=DoDEngineSettings(threshold=0.8),
    )
    dod = engine.derive(
        request="execute",
        context={CONTEXT_KEY_ENTITY_ID: "task_42"},
    )

    assert [c.name for c in dod.criteria] == ["x"]
    assert dod.confidence == 0.3
    assert len(dod.clarification_needed) == 1
    assert dod._provenance["entity_frontmatter"] == ["x"]
    assert dod._provenance["user_clarification"] == []
    assert dod.is_satisfied_for_act() is False
