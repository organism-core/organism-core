from __future__ import annotations

from dataclasses import dataclass

from organism.settings import SettingsBase, register_settings


@register_settings("dod_engine")
@dataclass
class DoDEngineSettings(SettingsBase):
    threshold: float = 0.8


@register_settings("entity_frontmatter")
@dataclass
class EntityFrontmatterSettings(SettingsBase):
    confidence_when_loaded: float = 0.5


@register_settings("domain_pattern")
@dataclass
class DomainPatternSettings(SettingsBase):
    confidence_per_pattern: float = 0.15
    max_confidence_delta: float = 0.4

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence_per_pattern <= 1.0:
            raise ValueError(
                "confidence_per_pattern must be in [0, 1], "
                f"got {self.confidence_per_pattern}"
            )
        if not 0.0 <= self.max_confidence_delta <= 1.0:
            raise ValueError(
                "max_confidence_delta must be in [0, 1], "
                f"got {self.max_confidence_delta}"
            )


@register_settings("related_entities")
@dataclass
class RelatedEntitiesSettings(SettingsBase):
    prefix_separator: str = "_"
    tags_frontmatter_key: str = "tags"
    tags_min_overlap: int = 1
    max_related: int = 10
    confidence_per_related: float = 0.05
    max_confidence_delta: float = 0.3
    cross_entity_weight_factor: float = 0.5

    def __post_init__(self) -> None:
        if not self.prefix_separator:
            raise ValueError("prefix_separator must be non-empty")
        if not self.tags_frontmatter_key:
            raise ValueError("tags_frontmatter_key must be non-empty")
        if self.tags_min_overlap < 1:
            raise ValueError(
                f"tags_min_overlap must be >= 1, got {self.tags_min_overlap}"
            )
        if self.max_related < 1:
            raise ValueError(
                f"max_related must be >= 1, got {self.max_related}"
            )
        if not 0.0 <= self.confidence_per_related <= 1.0:
            raise ValueError(
                "confidence_per_related must be in [0, 1], "
                f"got {self.confidence_per_related}"
            )
        if not 0.0 <= self.max_confidence_delta <= 1.0:
            raise ValueError(
                "max_confidence_delta must be in [0, 1], "
                f"got {self.max_confidence_delta}"
            )
        if not 0.0 <= self.cross_entity_weight_factor <= 1.0:
            raise ValueError(
                "cross_entity_weight_factor must be in [0, 1], "
                f"got {self.cross_entity_weight_factor}"
            )


@register_settings("vector_search")
@dataclass
class VectorSearchSettings(SettingsBase):
    n_results: int = 10
    max_distance: float = 1.0
    confidence_per_result: float = 0.05
    max_confidence_delta: float = 0.5
    fail_silently: bool = True

    def __post_init__(self) -> None:
        if self.n_results < 1:
            raise ValueError(
                f"n_results must be >= 1, got {self.n_results}"
            )
        if self.max_distance < 0.0:
            raise ValueError(
                f"max_distance must be >= 0, got {self.max_distance}"
            )
        if not 0.0 <= self.confidence_per_result <= 1.0:
            raise ValueError(
                "confidence_per_result must be in [0, 1], "
                f"got {self.confidence_per_result}"
            )
        if not 0.0 <= self.max_confidence_delta <= 1.0:
            raise ValueError(
                "max_confidence_delta must be in [0, 1], "
                f"got {self.max_confidence_delta}"
            )
