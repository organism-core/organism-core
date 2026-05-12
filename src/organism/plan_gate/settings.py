from __future__ import annotations

from dataclasses import dataclass

from organism.settings import SettingsBase, register_settings


@register_settings("plan_gate")
@dataclass
class PlanGateSettings(SettingsBase):
    require_decision_reason: bool = False
