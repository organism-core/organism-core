from organism.orchestrator.settings import OrchestratorSettings
from organism.orchestrator.types import (
    REVISION_OUTCOME_COMPLETED,
    REVISION_OUTCOME_ESCALATED,
    REVISION_OUTCOME_EXHAUSTED,
    REVISION_OUTCOME_FAILED,
    REVISION_OUTCOME_NONE,
    REVISION_OUTCOME_ROLLED_BACK,
    ActionResult,
    ActionStatus,
)

__all__ = [
    "ActionOrchestrator",
    "ActionResult",
    "ActionStatus",
    "OrchestratorSettings",
    "REVISION_OUTCOME_COMPLETED",
    "REVISION_OUTCOME_ESCALATED",
    "REVISION_OUTCOME_EXHAUSTED",
    "REVISION_OUTCOME_FAILED",
    "REVISION_OUTCOME_NONE",
    "REVISION_OUTCOME_ROLLED_BACK",
]


def __getattr__(name: str):
    if name == "ActionOrchestrator":
        from organism.orchestrator.orchestrator import ActionOrchestrator as _AO

        return _AO
    raise AttributeError(
        f"module 'organism.orchestrator' has no attribute {name!r}"
    )
