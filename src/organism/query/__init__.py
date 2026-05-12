"""Read-only query path for organism-core.

A consumer-facing parallel lineage to ``organism.adapter`` /
``organism.orchestrator``. Use it when a tool returns data but has no
side effects and no acceptance-criterion check (i.e., deterministic
reads). For probabilistic reads that need DoD-validation (OCR,
vector-search-ranking, classification), use ``BaseEffector`` /
``ReadEffector`` with ``ActionOrchestrator`` instead.

    Querier              two-method Protocol (pre_load, query)
    BaseQuerier          default base class — override query (raises)
    QueryRunner          read-only counterpart to ActionOrchestrator
    QueryResult          schlank: status / result / error / latency_ms
    QueryStatus          OK | ERROR
    QueryRunnerSettings  trace / truncation / event-emission tunables
"""

from organism.query.base import BaseQuerier
from organism.query.querier import Querier
from organism.query.runner import QueryRunner
from organism.query.settings import QueryRunnerSettings
from organism.query.types import QueryResult, QueryStatus

__all__ = [
    "BaseQuerier",
    "Querier",
    "QueryResult",
    "QueryRunner",
    "QueryRunnerSettings",
    "QueryStatus",
]
