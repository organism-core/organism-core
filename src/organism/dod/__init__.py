from __future__ import annotations

from typing import TYPE_CHECKING

from organism.dod.engine import DoDEngine
from organism.dod.evaluators import (
    EvaluationContext,
    Evaluator,
    LlmJudgeEvaluator,
    RuleEvaluator,
    SelfCheckEvaluator,
    default_evaluators,
)
from organism.dod.settings import DoDEngineSettings, EntityFrontmatterSettings
from organism.dod.source import DoDSource
from organism.dod.sources import (
    DomainPatternSource,
    EntityFrontmatterSource,
    LessonsSource,
    RelatedEntitiesSource,
    UserClarificationSource,
    VectorSearchSource,
)
from organism.dod.types import (
    EVALUATOR_LLM_JUDGE,
    EVALUATOR_RULE,
    EVALUATOR_SELF_CHECK,
    EVALUATORS,
    REVISION_ESCALATE_TO_HUMAN,
    REVISION_RETRY_ALT_PARAMS,
    REVISION_ROLLBACK_AND_LOG,
    REVISION_STRATEGIES,
    REVISION_STRATEGY_PRIORITY,
    Criterion,
    DoD,
    SourceContribution,
)
from organism.dod.validator import (
    CriterionResult,
    DoDValidator,
    ValidationResult,
)
from organism.memory import EntityStore

if TYPE_CHECKING:
    from organism.lessons.aggregator import LessonsAggregator

__all__ = [
    "Criterion",
    "CriterionResult",
    "DoD",
    "DoDEngine",
    "DoDEngineSettings",
    "DoDSource",
    "DoDValidator",
    "DomainPatternSource",
    "EVALUATOR_LLM_JUDGE",
    "EVALUATOR_RULE",
    "EVALUATOR_SELF_CHECK",
    "EVALUATORS",
    "EntityFrontmatterSettings",
    "EntityFrontmatterSource",
    "EvaluationContext",
    "Evaluator",
    "LessonsSource",
    "LlmJudgeEvaluator",
    "REVISION_ESCALATE_TO_HUMAN",
    "REVISION_RETRY_ALT_PARAMS",
    "REVISION_ROLLBACK_AND_LOG",
    "REVISION_STRATEGIES",
    "REVISION_STRATEGY_PRIORITY",
    "RelatedEntitiesSource",
    "RuleEvaluator",
    "SelfCheckEvaluator",
    "SourceContribution",
    "UserClarificationSource",
    "ValidationResult",
    "VectorSearchSource",
    "default_evaluators",
    "default_sources",
]


def default_sources(
    *,
    entity_store: EntityStore,
    lesson_aggregator: "LessonsAggregator | None" = None,
) -> list[DoDSource]:
    return [
        EntityFrontmatterSource(store=entity_store),
        LessonsSource(aggregator=lesson_aggregator),
        RelatedEntitiesSource(store=entity_store),
        VectorSearchSource(),
        DomainPatternSource(),
        UserClarificationSource(),
    ]
