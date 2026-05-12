from __future__ import annotations

from dataclasses import dataclass, field

from organism.dod.types import REVISION_RETRY_ALT_PARAMS, REVISION_STRATEGIES
from organism.settings import SettingsBase, register_settings

REVISION_LESSON_SOURCE = "dod_failure"
REVISION_LESSON_CRITERION_WEIGHT_FACTOR = 0.5

ON_DEFINITION_ASK = "ask"
ON_DEFINITION_ABORT = "abort"
ON_DEFINITION_PROCEED_WITH_WARNING = "proceed_with_warning"
ON_DEFINITION_UNCLEAR_MODES = frozenset(
    {
        ON_DEFINITION_ASK,
        ON_DEFINITION_ABORT,
        ON_DEFINITION_PROCEED_WITH_WARNING,
    }
)

ON_FULFILLMENT_WARN = "warn"
ON_FULFILLMENT_RETRY = "retry"
ON_FULFILLMENT_ABORT = "abort"
ON_FULFILLMENT_FAILED_MODES = frozenset(
    {
        ON_FULFILLMENT_WARN,
        ON_FULFILLMENT_RETRY,
        ON_FULFILLMENT_ABORT,
    }
)


@register_settings("orchestrator")
@dataclass
class OrchestratorSettings(SettingsBase):
    autonomous_max_revision_attempts: int = 2
    lesson_context_keys: list[str] = field(default_factory=list)
    revision_lesson_weight_factor: float = REVISION_LESSON_CRITERION_WEIGHT_FACTOR
    default_revision_strategy: str = REVISION_RETRY_ALT_PARAMS
    on_definition_unclear: str = ON_DEFINITION_ASK
    on_fulfillment_failed: str = ON_FULFILLMENT_WARN
    fulfillment_score_pass: float = 1.0

    def __post_init__(self) -> None:
        if self.autonomous_max_revision_attempts < 0:
            raise ValueError(
                "autonomous_max_revision_attempts must be >= 0, "
                f"got {self.autonomous_max_revision_attempts}"
            )
        if not 0.0 <= self.revision_lesson_weight_factor <= 1.0:
            raise ValueError(
                "revision_lesson_weight_factor must be in [0, 1], "
                f"got {self.revision_lesson_weight_factor}"
            )
        if any(not isinstance(k, str) or not k for k in self.lesson_context_keys):
            raise ValueError(
                "lesson_context_keys entries must be non-empty strings, "
                f"got {self.lesson_context_keys!r}"
            )
        if self.default_revision_strategy not in REVISION_STRATEGIES:
            raise ValueError(
                "default_revision_strategy must be one of "
                f"{sorted(REVISION_STRATEGIES)}, got "
                f"{self.default_revision_strategy!r}"
            )
        if self.on_definition_unclear not in ON_DEFINITION_UNCLEAR_MODES:
            raise ValueError(
                "on_definition_unclear must be one of "
                f"{sorted(ON_DEFINITION_UNCLEAR_MODES)}, got "
                f"{self.on_definition_unclear!r}"
            )
        if self.on_fulfillment_failed not in ON_FULFILLMENT_FAILED_MODES:
            raise ValueError(
                "on_fulfillment_failed must be one of "
                f"{sorted(ON_FULFILLMENT_FAILED_MODES)}, got "
                f"{self.on_fulfillment_failed!r}"
            )
        if not 0.0 <= self.fulfillment_score_pass <= 1.0:
            raise ValueError(
                "fulfillment_score_pass must be in [0, 1], "
                f"got {self.fulfillment_score_pass}"
            )
