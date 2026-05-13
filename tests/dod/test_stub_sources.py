from pathlib import Path

import pytest

from organism.dod import (
    DoD,
    DoDEngine,
    DoDEngineSettings,
    DoDSource,
    DomainPatternSource,
    EntityFrontmatterSource,
    RelatedEntitiesSource,
    UserClarificationSource,
    VectorSearchSource,
    default_sources,
)
from organism.dod.sources.entity_frontmatter import CONTEXT_KEY_ENTITY_ID
from organism.memory import Entity, EntityStore

ALL_STUB_CLASSES = [
    RelatedEntitiesSource,
    VectorSearchSource,
    DomainPatternSource,
]


@pytest.mark.parametrize("cls", ALL_STUB_CLASSES)
def test_stub_satisfies_protocol(cls):
    assert isinstance(cls(), DoDSource)


@pytest.mark.parametrize("cls", ALL_STUB_CLASSES)
def test_stub_contributes_empty(cls):
    contribution = cls().contribute(
        request="any", context={}, current=DoD()
    )
    assert contribution.criteria == []
    assert contribution.clarifications == []
    assert contribution.confidence_delta == 0.0
    assert contribution.evidence == {}


@pytest.mark.parametrize("cls", ALL_STUB_CLASSES)
def test_stub_records_no_provenance_in_engine(cls):
    engine = DoDEngine(sources=[cls()], settings=DoDEngineSettings(threshold=99.0))
    dod = engine.derive(request="any")
    assert dod._provenance == {}
    assert dod.criteria == []
    assert dod.confidence == 0.0


def test_stub_names_are_unique_and_match_canonical_order():
    names = [cls.name for cls in ALL_STUB_CLASSES]
    assert names == [
        "related_entities",
        "vector_search",
        "domain_pattern",
    ]
    assert len(set(names)) == len(names)


def test_related_entities_source_accepts_store_arg(tmp_path: Path):
    store = EntityStore(tmp_path)
    src = RelatedEntitiesSource(store=store)
    assert src.store is store


def test_related_entities_source_default_store_is_none():
    assert RelatedEntitiesSource().store is None


def test_vector_search_source_accepts_client_arg():
    sentinel = object()
    src = VectorSearchSource(client=sentinel)
    assert src.client is sentinel


def test_vector_search_source_default_client_is_none():
    assert VectorSearchSource().client is None


def test_domain_pattern_source_accepts_registry_arg():
    sentinel = object()
    src = DomainPatternSource(registry=sentinel)
    assert src.registry is sentinel


def test_domain_pattern_source_default_registry_is_none():
    assert DomainPatternSource().registry is None


def test_default_sources_returns_canonical_order(tmp_path: Path):
    """``related_entities`` and ``domain_pattern`` each split into two
    instances (prefix/tags, tuple/action_only) so the engine emits
    separate provenance buckets."""
    store = EntityStore(tmp_path)
    sources = default_sources(entity_store=store)
    assert [s.name for s in sources] == [
        "entity_frontmatter",
        "lessons",
        "related_entities:prefix",
        "related_entities:tags",
        "vector_search",
        "domain_pattern:tuple",
        "domain_pattern:action_only",
        "user_clarification",
    ]


def test_default_sources_all_satisfy_protocol(tmp_path: Path):
    store = EntityStore(tmp_path)
    for source in default_sources(entity_store=store):
        assert isinstance(source, DoDSource)


def test_default_sources_threads_entity_store_to_entity_dependent_sources(
    tmp_path: Path,
):
    store = EntityStore(tmp_path)
    sources = default_sources(entity_store=store)

    by_name = {s.name: s for s in sources}
    assert by_name["entity_frontmatter"].store is store
    assert by_name["related_entities:prefix"].store is store
    assert by_name["related_entities:tags"].store is store


def test_full_six_source_pipeline_only_active_sources_in_provenance(
    tmp_path: Path,
):
    store = EntityStore(tmp_path)
    store.write(
        "alpha",
        Entity(
            frontmatter={
                "dod": {
                    "criteria": [
                        {"name": "x", "expected": 1},
                        {"name": "y", "expected": 2},
                    ]
                }
            },
            body="",
        ),
    )

    engine = DoDEngine(
        sources=default_sources(entity_store=store),
        settings=DoDEngineSettings(threshold=0.8),
    )
    dod = engine.derive(
        request="any",
        context={CONTEXT_KEY_ENTITY_ID: "alpha"},
    )

    assert [c.name for c in dod.criteria] == ["x", "y"]
    assert all(c.source == "entity_frontmatter" for c in dod.criteria)
    assert len(dod.clarification_needed) == 1

    assert "entity_frontmatter" in dod._provenance
    assert "user_clarification" in dod._provenance
    assert "lessons" not in dod._provenance
    assert "related_entities" not in dod._provenance
    assert "vector_search" not in dod._provenance
    assert "domain_pattern" not in dod._provenance


def test_full_six_source_pipeline_early_stop_when_entity_satisfies(
    tmp_path: Path,
):
    store = EntityStore(tmp_path)
    store.write(
        "alpha",
        Entity(
            frontmatter={
                "dod": {"criteria": [{"name": "x", "expected": 1}]}
            },
            body="",
        ),
    )

    engine = DoDEngine(
        sources=default_sources(entity_store=store),
        settings=DoDEngineSettings(threshold=0.4),
    )
    dod = engine.derive(
        request="any",
        context={CONTEXT_KEY_ENTITY_ID: "alpha"},
    )

    assert dod.confidence == 0.5
    assert dod.clarification_needed == []
    assert "user_clarification" not in dod._provenance
