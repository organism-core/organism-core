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
from organism.dod.settings import (
    DoDEngineSettings,
    DomainPatternSettings,
    EntityFrontmatterSettings,
    RelatedEntitiesSettings,
    VectorSearchSettings,
)
from organism.dod.source import DoDSource
from organism.dod.sources import (
    CROSS_KIND_CRITERION_SOURCE,
    CrossDomainLessonsSource,
    DomainPatternSource,
    EntityFrontmatterSource,
    LessonsSource,
    MarkdownRubricSource,
    PatternRegistry,
    RelatedEntitiesSource,
    UserClarificationSource,
    VectorSearchSource,
    parse_rubric,
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
    "CROSS_KIND_CRITERION_SOURCE",
    "Criterion",
    "CriterionResult",
    "CrossDomainLessonsSource",
    "DoD",
    "DoDEngine",
    "DoDEngineSettings",
    "DoDSource",
    "DoDValidator",
    "DomainPatternSettings",
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
    "MarkdownRubricSource",
    "PatternRegistry",
    "REVISION_ESCALATE_TO_HUMAN",
    "REVISION_RETRY_ALT_PARAMS",
    "REVISION_ROLLBACK_AND_LOG",
    "REVISION_STRATEGIES",
    "REVISION_STRATEGY_PRIORITY",
    "RelatedEntitiesSettings",
    "RelatedEntitiesSource",
    "RuleEvaluator",
    "SelfCheckEvaluator",
    "SourceContribution",
    "UserClarificationSource",
    "ValidationResult",
    "VectorSearchSettings",
    "VectorSearchSource",
    "default_evaluators",
    "default_sources",
    "parse_rubric",
]


def default_sources(
    *,
    entity_store: EntityStore,
    lesson_aggregator: "LessonsAggregator | None" = None,
    pattern_registry: "PatternRegistry | None" = None,
    vector_search_client: object | None = None,
) -> list[DoDSource]:
    """Canonical M5 pipeline.

    Returns eight sources in the order the engine will consult them:

    1. ``entity_frontmatter`` — DoD criteria stored on the entity itself.
    2. ``lessons`` — same-kind lesson criteria_hint.
    3. ``related_entities:prefix`` — prefix-cluster siblings'
       criteria.
    4. ``related_entities:tags`` — tag-overlap siblings' criteria.
    5. ``vector_search`` — top-K similar past actions.
    6. ``domain_pattern:tuple`` — registry lookup by
       ``(action_type, entity_type)``.
    7. ``domain_pattern:action_only`` — registry lookup by
       ``action_type`` alone.
    8. ``user_clarification`` — fallback when confidence stays below
       threshold.

    ``related_entities`` and ``domain_pattern`` ship as two source
    instances each so that the engine emits separate provenance
    buckets (``…:prefix``/``…:tags`` and ``…:tuple``/``…:action_only``).
    """
    return [
        EntityFrontmatterSource(store=entity_store),
        LessonsSource(aggregator=lesson_aggregator),
        RelatedEntitiesSource(
            store=entity_store,
            lookup_mode=RelatedEntitiesSource.MODE_PREFIX,
        ),
        RelatedEntitiesSource(
            store=entity_store,
            lookup_mode=RelatedEntitiesSource.MODE_TAGS,
        ),
        VectorSearchSource(client=vector_search_client),
        DomainPatternSource(
            registry=pattern_registry,
            lookup_mode=DomainPatternSource.MODE_TUPLE,
        ),
        DomainPatternSource(
            registry=pattern_registry,
            lookup_mode=DomainPatternSource.MODE_ACTION_ONLY,
        ),
        UserClarificationSource(),
    ]
