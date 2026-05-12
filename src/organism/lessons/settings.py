from __future__ import annotations

from dataclasses import dataclass

from organism.settings import SettingsBase, register_settings


@register_settings("lessons_aggregator")
@dataclass
class LessonsAggregatorSettings(SettingsBase):
    query_max_results: int = 10

    def __post_init__(self) -> None:
        if self.query_max_results <= 0:
            raise ValueError(
                "query_max_results must be > 0, "
                f"got {self.query_max_results}"
            )


@register_settings("lessons_source")
@dataclass
class LessonsSourceSettings(SettingsBase):
    max_confidence_delta: float = 0.5

    def __post_init__(self) -> None:
        if not 0.0 <= self.max_confidence_delta <= 1.0:
            raise ValueError(
                "max_confidence_delta must be in [0, 1], "
                f"got {self.max_confidence_delta}"
            )
