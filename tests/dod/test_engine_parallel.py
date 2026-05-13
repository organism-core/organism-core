"""Tests for DoDEngine's parallel dispatch mode.

When ``parallel=True`` is passed at construction, the engine
dispatches all sources concurrently via a ``ThreadPoolExecutor``,
merges the results in deterministic order, and dedupes criteria by
name. Early-exit is disabled in this mode; all sources run.

The default (``parallel=False``) path is covered by the existing
``test_engine.py`` suite — these tests focus on the parallel-only
behaviors and trade-offs.
"""

from __future__ import annotations

import threading
import time
from typing import Any

from organism.dod import (
    Criterion,
    DoD,
    DoDEngine,
    DoDEngineSettings,
    SourceContribution,
)


class _RecordingSource:
    """Source that records what `current` DoD it received and what it
    contributed."""

    def __init__(
        self,
        name: str,
        criteria: list[Criterion],
        *,
        confidence_delta: float = 0.0,
        clarifications: list[str] | None = None,
    ) -> None:
        self.name = name
        self._criteria = criteria
        self._confidence_delta = confidence_delta
        self._clarifications = list(clarifications or [])
        self.contribute_calls: list[DoD] = []

    def contribute(
        self,
        request: Any,
        context: dict[str, Any],
        current: DoD,
    ) -> SourceContribution:
        # Snapshot of what `current` looked like at call-time.
        self.contribute_calls.append(
            DoD(
                criteria=list(current.criteria),
                clarification_needed=list(current.clarification_needed),
                confidence=current.confidence,
            )
        )
        return SourceContribution(
            source_name=self.name,
            criteria=list(self._criteria),
            confidence_delta=self._confidence_delta,
            clarifications=list(self._clarifications),
        )


class _SleepingSource:
    """Source that sleeps for a fixed duration before returning. Used
    to verify that parallel dispatch actually overlaps."""

    def __init__(self, name: str, sleep_s: float):
        self.name = name
        self.sleep_s = sleep_s

    def contribute(self, request, context, current):
        time.sleep(self.sleep_s)
        return SourceContribution(
            source_name=self.name,
            criteria=[Criterion(name=f"{self.name}_c", expected=True)],
            confidence_delta=0.1,
        )


# ---------- Parallel sees empty DoD


def test_parallel_each_source_sees_empty_dod():
    s1 = _RecordingSource(
        name="s1",
        criteria=[Criterion(name="a", expected=True)],
        confidence_delta=0.5,
    )
    s2 = _RecordingSource(
        name="s2",
        criteria=[Criterion(name="b", expected=True)],
        confidence_delta=0.5,
    )

    engine = DoDEngine(sources=[s1, s2], parallel=True)
    engine.derive("r", {})

    # Both sources saw an empty DoD (no criteria from the other).
    assert len(s1.contribute_calls) == 1
    assert len(s2.contribute_calls) == 1
    assert s1.contribute_calls[0].criteria == []
    assert s2.contribute_calls[0].criteria == []


def test_sequential_sees_growing_dod():
    """Contrast test: in sequential mode each source sees the prior
    contributions in `current`."""
    s1 = _RecordingSource(
        name="s1",
        criteria=[Criterion(name="a", expected=True)],
        confidence_delta=0.1,
    )
    s2 = _RecordingSource(
        name="s2",
        criteria=[Criterion(name="b", expected=True)],
        confidence_delta=0.1,
    )
    engine = DoDEngine(
        sources=[s1, s2],
        settings=DoDEngineSettings(threshold=0.99),
        parallel=False,
    )
    engine.derive("r", {})

    # s2 should see s1's contribution in its `current`.
    s2_call = s2.contribute_calls[0]
    assert len(s2_call.criteria) == 1
    assert s2_call.criteria[0].name == "a"


# ---------- Merge order is deterministic


def test_parallel_merge_order_follows_sources_order_not_completion_order():
    """Even if a later source finishes first, the merge preserves
    sources-list order."""
    slow_first = _SleepingSource("first", sleep_s=0.05)
    fast_second = _SleepingSource("second", sleep_s=0.0)
    fast_third = _SleepingSource("third", sleep_s=0.0)

    engine = DoDEngine(
        sources=[slow_first, fast_second, fast_third], parallel=True
    )
    dod = engine.derive("r", {})

    names = [c.name for c in dod.criteria]
    assert names == ["first_c", "second_c", "third_c"]


# ---------- Parallel actually parallelizes


def test_parallel_overlaps_source_latency():
    """Three sources sleeping 0.1s each should complete in ~0.1s when
    parallel (max), not ~0.3s (sum)."""
    sources = [_SleepingSource(f"s{i}", sleep_s=0.1) for i in range(3)]
    engine = DoDEngine(sources=sources, parallel=True)

    start = time.monotonic()
    engine.derive("r", {})
    elapsed = time.monotonic() - start

    # Allow generous margin for thread-pool overhead.
    # Sequential would be >= 0.3; parallel should be well under 0.25.
    assert elapsed < 0.25, (
        f"parallel dispatch was {elapsed:.3f}s; expected < 0.25s "
        "(sequential would be ~0.3s)"
    )


# ---------- Dedup


def test_parallel_dedupes_duplicate_criterion_names():
    s1 = _RecordingSource(
        name="s1",
        criteria=[Criterion(name="shared", expected=True, weight=1.0)],
    )
    s2 = _RecordingSource(
        name="s2",
        criteria=[Criterion(name="shared", expected=True, weight=0.5)],
    )
    engine = DoDEngine(sources=[s1, s2], parallel=True)
    dod = engine.derive("r", {})

    # Exactly one "shared" in the final DoD.
    matching = [c for c in dod.criteria if c.name == "shared"]
    assert len(matching) == 1
    # First-source-wins (deterministic via sources order).
    assert matching[0].source == "s1"
    assert matching[0].weight == 1.0


def test_parallel_dedup_keeps_first_sources_version():
    """If two sources contribute the same criterion-name, the first
    one in the sources list keeps its version. Second is silently
    dropped."""
    s1 = _RecordingSource(
        name="s1",
        criteria=[Criterion(name="x", expected="value_from_s1")],
    )
    s2 = _RecordingSource(
        name="s2",
        criteria=[Criterion(name="x", expected="value_from_s2")],
    )
    engine = DoDEngine(sources=[s1, s2], parallel=True)
    dod = engine.derive("r", {})
    [c] = dod.criteria
    assert c.expected == "value_from_s1"


# ---------- Exception handling


class _RaisingSource:
    name = "boom"

    def contribute(self, request, context, current):
        raise RuntimeError("source failed")


def test_parallel_isolates_raising_source():
    """A raising source must not crash the engine or block other
    sources; the engine records the error as evidence."""
    raising = _RaisingSource()
    working = _RecordingSource(
        name="ok",
        criteria=[Criterion(name="a", expected=True)],
        confidence_delta=0.5,
    )
    engine = DoDEngine(sources=[raising, working], parallel=True)
    dod = engine.derive("r", {})

    # Working source's criterion is in the DoD.
    names = [c.name for c in dod.criteria]
    assert "a" in names

    # Raising source is in provenance with the error captured.
    # _merge_with_dedup adds the source-name to provenance when there's
    # either contributed criteria or evidence — and the error path
    # has evidence={"error": ...}.
    assert "boom" in dod._provenance
    # No criteria contributed by the raising source.
    assert dod._provenance["boom"] == []


# ---------- Early-exit disabled in parallel mode


def test_parallel_runs_all_sources_even_when_threshold_already_met():
    """Sequential mode would early-exit; parallel mode runs all
    sources regardless of accumulated confidence."""
    sources = [
        _RecordingSource(
            name=f"s{i}",
            criteria=[Criterion(name=f"c{i}", expected=True)],
            confidence_delta=1.0,  # any one source alone meets threshold=0.5
        )
        for i in range(3)
    ]
    engine = DoDEngine(
        sources=sources,
        settings=DoDEngineSettings(threshold=0.5),
        parallel=True,
    )
    dod = engine.derive("r", {})

    # All three sources contributed (no early-exit).
    assert len(dod.criteria) == 3


def test_sequential_early_exits_on_first_satisfied():
    """Contrast: sequential mode early-exits after first source if
    threshold reached."""
    sources = [
        _RecordingSource(
            name=f"s{i}",
            criteria=[Criterion(name=f"c{i}", expected=True)],
            confidence_delta=1.0,
        )
        for i in range(3)
    ]
    engine = DoDEngine(
        sources=sources,
        settings=DoDEngineSettings(threshold=0.5),
        parallel=False,
    )
    dod = engine.derive("r", {})

    # Only one source contributed (early-exit after s0).
    assert len(dod.criteria) == 1


# ---------- Empty sources list


def test_parallel_empty_sources_returns_empty_dod():
    engine = DoDEngine(sources=[], parallel=True)
    dod = engine.derive("r", {})
    assert dod.criteria == []
    assert dod.confidence == 0.0


# ---------- Settings round-trip


def test_parallel_flag_defaults_to_false():
    engine = DoDEngine(sources=[])
    assert engine.parallel is False


def test_max_workers_passes_through():
    engine = DoDEngine(sources=[], parallel=True, max_workers=4)
    assert engine.max_workers == 4


# ---------- Thread-safety smoke


def test_parallel_thread_count_under_load():
    """Twenty sources, each recording the thread it ran on. Verify
    they ran on multiple threads (parallel dispatch confirmed)."""
    threads_seen: list[int] = []
    lock = threading.Lock()

    class _ThreadRecorder:
        def __init__(self, name):
            self.name = name

        def contribute(self, request, context, current):
            with lock:
                threads_seen.append(threading.get_ident())
            time.sleep(0.01)  # ensure overlap
            return SourceContribution(source_name=self.name)

    sources = [_ThreadRecorder(name=f"s{i}") for i in range(20)]
    engine = DoDEngine(sources=sources, parallel=True)
    engine.derive("r", {})

    # If parallel dispatch is working, more than 1 thread ran sources.
    assert len(set(threads_seen)) > 1


# ---------- Mixed-sources integration


def test_parallel_with_mixed_real_sources(tmp_path):
    """Integration: an EntityFrontmatterSource + a recorded synthetic
    source, both running in parallel."""
    from organism.dod import EntityFrontmatterSource
    from organism.memory import Entity, EntityStore

    store = EntityStore(tmp_path / "entities")
    store.write(
        "ent_1",
        Entity(
            frontmatter={
                "dod": {
                    "criteria": [
                        {"name": "from_fm", "expected": True, "weight": 1.0}
                    ]
                }
            },
            body="",
        ),
    )

    fm_source = EntityFrontmatterSource(store=store)
    extra_source = _RecordingSource(
        name="extra",
        criteria=[Criterion(name="from_extra", expected=True)],
        confidence_delta=0.2,
    )

    engine = DoDEngine(sources=[fm_source, extra_source], parallel=True)
    dod = engine.derive(
        "r", context={"entity_id": "ent_1"}
    )

    names = {c.name for c in dod.criteria}
    assert names == {"from_fm", "from_extra"}
    # Both providers in provenance.
    assert "entity_frontmatter" in dod._provenance
    assert "extra" in dod._provenance
