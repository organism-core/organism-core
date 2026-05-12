from __future__ import annotations

from dataclasses import dataclass

from organism.lifecycle.types import LifecycleStage
from organism.settings import SettingsBase, register_settings


@register_settings("lifecycle")
@dataclass
class LifecycleSettings(SettingsBase):
    initial_stage: str = "proposed"
    promote_after_n: int = 30
    promote_score_threshold: float = 0.9
    demote_after_n: int = 5
    demote_score_threshold: float = 0.7
    window_size: int = 50

    def __post_init__(self) -> None:
        valid_stages = [s.value for s in LifecycleStage]
        if self.initial_stage not in valid_stages:
            raise ValueError(
                f"initial_stage must be one of {valid_stages}, "
                f"got {self.initial_stage!r}"
            )
        if self.promote_after_n <= 0:
            raise ValueError("promote_after_n must be > 0")
        if self.demote_after_n <= 0:
            raise ValueError("demote_after_n must be > 0")
        if self.window_size < max(self.promote_after_n, self.demote_after_n):
            raise ValueError(
                "window_size must be >= max(promote_after_n, demote_after_n)"
            )
        if not 0.0 <= self.promote_score_threshold <= 1.0:
            raise ValueError(
                "promote_score_threshold must be in [0, 1]"
            )
        if not 0.0 <= self.demote_score_threshold <= 1.0:
            raise ValueError(
                "demote_score_threshold must be in [0, 1]"
            )
