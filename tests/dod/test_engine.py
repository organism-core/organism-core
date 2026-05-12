from typing import Any

import pytest

from organism.dod import (
    Criterion,
    DoD,
    DoDEngine,
    DoDEngineSettings,
    DoDSource,
    SourceContribution,
)


class _StaticSource:
    def __init__(
        self,
        name: str,
        criteria: list[Criterion] | None = None,
        confidence_delta: float = 0.0,
        clarifications: list[str] | None = None,
        evidence: dict[str, Any] | None = None,
    ) -> None:
        self.name = name
        self._criteria = criteria or []
        self._confidence_delta = confidence_delta
        self._clarifications = clarifications or []
        self._evidence = evidence or {}
        self.call_count = 0

    def contribute(
        self,
        request: Any,
        context: dict[str, Any],
        current: DoD,
    ) -> SourceContribution:
        self.call_count += 1
        return SourceContribution(
            source_name=self.name,
            criteria=[
                Criterion(name=c.name, expected=c.expected, weight=c.weight)
                for c in self._criteria
            ],
            confidence_delta=self._confidence_delta,
            clarifications=list(self._clarifications),
            evidence=dict(self._evidence),
        )


def test_static_source_satisfies_protocol():
    assert isinstance(_StaticSource("x"), DoDSource)


def test_engine_with_no_sources_returns_empty_dod():
    engine = DoDEngine(sources=[])
    dod = engine.derive(request="any", context={})
    assert dod.criteria == []
    assert dod.clarification_needed == []
    assert dod.confidence == 0.0


def test_engine_collects_criteria_and_stamps_source():
    source = _StaticSource(
        name="entity",
        criteria=[Criterion(name="must_have_id", expected=True)],
        confidence_delta=0.5,
    )
    engine = DoDEngine(sources=[source])
    dod = engine.derive(request="any")
    assert [c.name for c in dod.criteria] == ["must_have_id"]
    assert dod.criteria[0].source == "entity"
    assert dod.confidence == 0.5


def test_engine_does_not_mutate_source_internal_criteria():
    original = Criterion(name="x", expected=1)
    source = _StaticSource(name="entity", criteria=[original])
    engine = DoDEngine(sources=[source])
    engine.derive(request="any")
    assert original.source == ""


def test_engine_early_stops_at_threshold():
    a = _StaticSource(name="a", confidence_delta=0.5)
    b = _StaticSource(name="b", confidence_delta=0.4)
    c = _StaticSource(name="c", confidence_delta=0.4)
    engine = DoDEngine(sources=[a, b, c], settings=DoDEngineSettings(threshold=0.8))
    dod = engine.derive(request="any")
    assert a.call_count == 1
    assert b.call_count == 1
    assert c.call_count == 0
    assert dod.confidence == pytest.approx(0.9)


def test_engine_does_not_stop_if_clarifications_pending():
    a = _StaticSource(
        name="a", confidence_delta=1.0, clarifications=["?"]
    )
    b = _StaticSource(name="b", confidence_delta=0.0)
    engine = DoDEngine(sources=[a, b], settings=DoDEngineSettings(threshold=0.8))
    dod = engine.derive(request="any")
    assert a.call_count == 1
    assert b.call_count == 1
    assert dod.clarification_needed == ["?"]


def test_engine_caps_confidence_at_one():
    a = _StaticSource(name="a", confidence_delta=0.7)
    b = _StaticSource(name="b", confidence_delta=0.7)
    engine = DoDEngine(sources=[a, b], settings=DoDEngineSettings(threshold=99.0))
    dod = engine.derive(request="any")
    assert dod.confidence == 1.0


def test_engine_floors_confidence_at_zero():
    a = _StaticSource(name="a", confidence_delta=-0.5)
    engine = DoDEngine(sources=[a], settings=DoDEngineSettings(threshold=99.0))
    dod = engine.derive(request="any")
    assert dod.confidence == 0.0


def test_engine_provenance_records_source_to_criterion_mapping():
    a = _StaticSource(
        name="entity",
        criteria=[
            Criterion(name="x", expected=1),
            Criterion(name="y", expected=2),
        ],
    )
    b = _StaticSource(
        name="lessons",
        criteria=[Criterion(name="z", expected=3)],
    )
    engine = DoDEngine(sources=[a, b], settings=DoDEngineSettings(threshold=99.0))
    dod = engine.derive(request="any")
    assert dod._provenance == {"entity": ["x", "y"], "lessons": ["z"]}


def test_engine_provenance_records_source_with_evidence_only():
    a = _StaticSource(name="entity", evidence={"looked_up": "alpha"})
    engine = DoDEngine(sources=[a], settings=DoDEngineSettings(threshold=99.0))
    dod = engine.derive(request="any")
    assert "entity" in dod._provenance
    assert dod._provenance["entity"] == []


def test_engine_provenance_skips_silent_sources():
    a = _StaticSource(name="silent")
    engine = DoDEngine(sources=[a], settings=DoDEngineSettings(threshold=99.0))
    dod = engine.derive(request="any")
    assert "silent" not in dod._provenance


def test_engine_clarifications_accumulate_in_priority_order():
    a = _StaticSource(name="a", clarifications=["q1"])
    b = _StaticSource(name="b", clarifications=["q2", "q3"])
    engine = DoDEngine(sources=[a, b], settings=DoDEngineSettings(threshold=99.0))
    dod = engine.derive(request="any")
    assert dod.clarification_needed == ["q1", "q2", "q3"]


def test_engine_passes_request_and_context_to_each_source():
    seen: list[tuple[Any, dict[str, Any]]] = []

    class _Recorder:
        name = "recorder"

        def contribute(
            self,
            request: Any,
            context: dict[str, Any],
            current: DoD,
        ) -> SourceContribution:
            seen.append((request, dict(context)))
            return SourceContribution(source_name=self.name)

    engine = DoDEngine(sources=[_Recorder(), _Recorder()])
    engine.derive(request="task_x", context={"k": "v"})
    assert seen == [("task_x", {"k": "v"}), ("task_x", {"k": "v"})]


def test_engine_does_not_pollute_caller_context():
    class _Mutator:
        name = "mutator"

        def contribute(
            self,
            request: Any,
            context: dict[str, Any],
            current: DoD,
        ) -> SourceContribution:
            context["injected"] = True
            return SourceContribution(source_name=self.name)

    caller_ctx = {"original": True}
    engine = DoDEngine(sources=[_Mutator()])
    engine.derive(request="any", context=caller_ctx)
    assert caller_ctx == {"original": True}
