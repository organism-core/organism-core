"""Querier-side Trenn-Test-Wächter — parallel zu test_cross_demo.py.

Verifies that the read-only Querier path is generic across the three
demo domains: same Protocol surface, same QueryRunner invocation
shape, same trace-count outcome. If a domain-specific assumption
sneaks into the query lineage, this test fails before the action-side
counterpart even runs.
"""

from __future__ import annotations

from pathlib import Path

from organism.observability import QueryTraceStore
from organism.query import QueryRunner, QueryStatus

from examples.architect_lite.querier import FloorPlanQuerier
from examples.cfo_lite.querier import CostCenterQuerier
from examples.tax_lite.querier import TaxReturnQuerier

ARCH_KIND = "lookup_floor_plan"
TAX_KIND = "lookup_tax_return"
CFO_KIND = "lookup_cost_center"


def _make_runner(tmp_path: Path) -> tuple[QueryRunner, QueryTraceStore]:
    store = QueryTraceStore(tmp_path / "qtraces")
    return QueryRunner(trace_store=store), store


# Identity-check — all three queriers satisfy the Protocol.


def test_all_three_queriers_satisfy_querier_protocol():
    from organism.query import Querier

    arch = FloorPlanQuerier(return_map={"a": 1})
    tax = TaxReturnQuerier(return_map={"a": 1})
    cfo = CostCenterQuerier(return_map={"a": 1})
    assert isinstance(arch, Querier)
    assert isinstance(tax, Querier)
    assert isinstance(cfo, Querier)


def test_all_three_queriers_inherit_from_base_querier():
    from organism.query import BaseQuerier

    assert isinstance(FloorPlanQuerier({}), BaseQuerier)
    assert isinstance(TaxReturnQuerier({}), BaseQuerier)
    assert isinstance(CostCenterQuerier({}), BaseQuerier)


def test_all_three_queriers_have_distinct_names():
    names = {
        FloorPlanQuerier({}).name,
        TaxReturnQuerier({}).name,
        CostCenterQuerier({}).name,
    }
    assert len(names) == 3


# Same shape — same number of traces, same status distribution.


def test_same_call_count_produces_same_trace_count_per_domain(tmp_path: Path):
    arch_runner, arch_store = _make_runner(tmp_path / "arch")
    tax_runner, tax_store = _make_runner(tmp_path / "tax")
    cfo_runner, cfo_store = _make_runner(tmp_path / "cfo")

    arch_q = FloorPlanQuerier(return_map={"e1": {"rooms": 4}, "e2": {"rooms": 7}})
    tax_q = TaxReturnQuerier(return_map={"e1": {"income": 50000}, "e2": {"income": 80000}})
    cfo_q = CostCenterQuerier(return_map={"e1": {"balance": 1.0}, "e2": {"balance": 2.0}})

    for r in ("e1", "e2", "e1"):
        arch_runner.execute(arch_q, kind=ARCH_KIND, request=r)
        tax_runner.execute(tax_q, kind=TAX_KIND, request=r)
        cfo_runner.execute(cfo_q, kind=CFO_KIND, request=r)

    assert len(arch_store.list()) == 3
    assert len(tax_store.list()) == 3
    assert len(cfo_store.list()) == 3


def test_same_error_behavior_across_domains(tmp_path: Path):
    arch_runner, arch_store = _make_runner(tmp_path / "arch")
    tax_runner, tax_store = _make_runner(tmp_path / "tax")
    cfo_runner, cfo_store = _make_runner(tmp_path / "cfo")

    # Empty return_maps -> every call hits the KeyError path.
    arch_q = FloorPlanQuerier(return_map={})
    tax_q = TaxReturnQuerier(return_map={})
    cfo_q = CostCenterQuerier(return_map={})

    arch_res = arch_runner.execute(arch_q, kind=ARCH_KIND, request="missing")
    tax_res = tax_runner.execute(tax_q, kind=TAX_KIND, request="missing")
    cfo_res = cfo_runner.execute(cfo_q, kind=CFO_KIND, request="missing")

    assert arch_res.status == QueryStatus.ERROR
    assert tax_res.status == QueryStatus.ERROR
    assert cfo_res.status == QueryStatus.ERROR

    # All three trace files are written with status ERROR.
    assert arch_store.list()[0].status == QueryStatus.ERROR
    assert tax_store.list()[0].status == QueryStatus.ERROR
    assert cfo_store.list()[0].status == QueryStatus.ERROR


def test_distinct_kinds_keep_traces_separated(tmp_path: Path):
    """All three demos share one QueryTraceStore; kind filtering must
    keep them apart cleanly."""
    runner, store = _make_runner(tmp_path)

    arch_q = FloorPlanQuerier(return_map={"e1": {}})
    tax_q = TaxReturnQuerier(return_map={"e1": {}})
    cfo_q = CostCenterQuerier(return_map={"e1": {}})

    runner.execute(arch_q, kind=ARCH_KIND, request="e1")
    runner.execute(arch_q, kind=ARCH_KIND, request="e1")
    runner.execute(tax_q, kind=TAX_KIND, request="e1")
    runner.execute(cfo_q, kind=CFO_KIND, request="e1")
    runner.execute(cfo_q, kind=CFO_KIND, request="e1")
    runner.execute(cfo_q, kind=CFO_KIND, request="e1")

    assert len(store.list(kind=ARCH_KIND)) == 2
    assert len(store.list(kind=TAX_KIND)) == 1
    assert len(store.list(kind=CFO_KIND)) == 3
    assert len(store.list()) == 6


def test_querier_caller_field_round_trips_through_trace(tmp_path: Path):
    runner, store = _make_runner(tmp_path)
    q = FloorPlanQuerier(return_map={"e1": {"rooms": 1}})
    runner.execute(q, kind=ARCH_KIND, request="e1", caller="ui:dashboard")
    trace = store.list()[0]
    assert trace.caller == "ui:dashboard"
