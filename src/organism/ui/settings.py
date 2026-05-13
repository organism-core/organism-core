from __future__ import annotations

from dataclasses import dataclass

from organism.settings import SettingsBase, register_settings


@register_settings("cockpit")
@dataclass
class CockpitSettings(SettingsBase):
    """Tunables for the headless Cockpit. All admin-UI-visible.

    payload_repr_max_length   how aggressively payload values are truncated
                              in PlanApprovalView.payload_summary
    trend_window              how many recent scores DriftView uses to
                              compute the trend bucket (improving/stable/
                              degrading)
    drift_warning_band        if avg(recent_scores) lands within this
                              distance above the demote threshold, the
                              DriftView's drift_warning flag fires
    plan_list_max_items       safety cap on Cockpit.pending_plans()
    show_resolved_plans       include APPROVED/REJECTED/APPLIED/EXPIRED in
                              pending_plans() listings (default False)
    """

    payload_repr_max_length: int = 120
    trend_window: int = 6
    drift_warning_band: float = 0.05
    plan_list_max_items: int = 50
    show_resolved_plans: bool = False
    # Lesson-pile observability window — see EffectorSummaryView's
    # lessons_recent_use_ratio. 7 days (604800 s) is the default
    # rhythm at which the pile-up signal becomes meaningful.
    lessons_recent_use_window_seconds: int = 604800

    def __post_init__(self) -> None:
        if self.payload_repr_max_length < 16:
            raise ValueError(
                "payload_repr_max_length must be >= 16, "
                f"got {self.payload_repr_max_length}"
            )
        if self.trend_window < 2:
            raise ValueError(
                "trend_window must be >= 2 (first/second half split), "
                f"got {self.trend_window}"
            )
        if not 0.0 <= self.drift_warning_band <= 1.0:
            raise ValueError(
                "drift_warning_band must be in [0, 1], "
                f"got {self.drift_warning_band}"
            )
        if self.plan_list_max_items <= 0:
            raise ValueError(
                "plan_list_max_items must be > 0, "
                f"got {self.plan_list_max_items}"
            )
        if self.lessons_recent_use_window_seconds <= 0:
            raise ValueError(
                "lessons_recent_use_window_seconds must be > 0, "
                f"got {self.lessons_recent_use_window_seconds}"
            )
