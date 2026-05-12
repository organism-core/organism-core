from organism.dod import Criterion, DoD, SourceContribution


def test_criterion_to_dict_minimal_omits_empty_source():
    c = Criterion(name="x", expected=42)
    assert c.to_dict() == {"name": "x", "expected": 42, "weight": 1.0}


def test_criterion_to_dict_includes_source_when_set():
    c = Criterion(name="x", expected=42, weight=0.5, source="entity")
    assert c.to_dict() == {
        "name": "x",
        "expected": 42,
        "weight": 0.5,
        "source": "entity",
    }


def test_source_contribution_defaults():
    sc = SourceContribution(source_name="x")
    assert sc.criteria == []
    assert sc.confidence_delta == 0.0
    assert sc.clarifications == []
    assert sc.evidence == {}


def test_dod_defaults_empty():
    dod = DoD()
    assert dod.criteria == []
    assert dod.clarification_needed == []
    assert dod.confidence == 0.0
    assert dod.evidence_sources == []
    assert dod._provenance == {}


def test_dod_is_satisfied_for_act_when_no_clarification():
    dod = DoD()
    assert dod.is_satisfied_for_act() is True
    dod.clarification_needed.append("?")
    assert dod.is_satisfied_for_act() is False


def test_dod_to_dict_matches_doc_schema():
    dod = DoD(
        criteria=[
            Criterion(name="rooms_count", expected="25..35", source="entity")
        ],
        clarification_needed=[],
        confidence=0.85,
        evidence_sources=["self_check"],
        _provenance={"entity": ["rooms_count"]},
    )
    assert dod.to_dict() == {
        "criteria": [
            {
                "name": "rooms_count",
                "expected": "25..35",
                "weight": 1.0,
                "source": "entity",
            }
        ],
        "clarification_needed": [],
        "confidence": 0.85,
        "evidence_sources": ["self_check"],
        "_provenance": {"entity": ["rooms_count"]},
    }


def test_dod_to_dict_returns_independent_copies():
    dod = DoD(
        clarification_needed=["?"],
        evidence_sources=["s"],
        _provenance={"x": ["y"]},
    )
    d = dod.to_dict()
    d["clarification_needed"].append("mutate")
    d["evidence_sources"].append("mutate")
    d["_provenance"]["x"].append("mutate")
    assert dod.clarification_needed == ["?"]
    assert dod.evidence_sources == ["s"]
    assert dod._provenance == {"x": ["y"]}


def test_criterion_from_dict_minimal():
    c = Criterion.from_dict({"name": "x", "expected": 42})
    assert c.name == "x"
    assert c.expected == 42
    assert c.weight == 1.0
    assert c.source == ""


def test_criterion_from_dict_full():
    c = Criterion.from_dict(
        {"name": "x", "expected": 42, "weight": 0.5, "source": "entity"}
    )
    assert c.weight == 0.5
    assert c.source == "entity"


def test_criterion_round_trip():
    original = Criterion(
        name="x", expected="25..35", weight=0.8, source="entity"
    )
    restored = Criterion.from_dict(original.to_dict())
    assert restored == original


def test_dod_from_dict_empty():
    dod = DoD.from_dict({})
    assert dod.criteria == []
    assert dod.clarification_needed == []
    assert dod.confidence == 0.0
    assert dod.evidence_sources == []
    assert dod._provenance == {}


def test_dod_round_trip_full():
    original = DoD(
        criteria=[
            Criterion(name="x", expected=1, source="entity"),
            Criterion(name="y", expected="ok", weight=0.5, source="entity"),
        ],
        clarification_needed=["q1"],
        confidence=0.7,
        evidence_sources=["self_check", "user_validation"],
        _provenance={"entity": ["x", "y"], "lessons": []},
    )
    restored = DoD.from_dict(original.to_dict())
    assert restored == original


def test_dod_from_dict_independent_from_source_dict():
    source = {
        "criteria": [{"name": "x", "expected": 1}],
        "clarification_needed": ["q"],
        "_provenance": {"a": ["b"]},
    }
    dod = DoD.from_dict(source)
    source["clarification_needed"].append("mutated")
    source["_provenance"]["a"].append("mutated")
    assert dod.clarification_needed == ["q"]
    assert dod._provenance == {"a": ["b"]}
