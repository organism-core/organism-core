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
