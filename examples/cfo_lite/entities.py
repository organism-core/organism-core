from __future__ import annotations

from typing import Any

ENTITIES: dict[str, dict[str, Any]] = {
    "2024-Q3": {
        "type": "quarterly_close",
        "fiscal_year": 2024,
        "quarter": 3,
        "dod": {
            "criteria": [
                {
                    "name": "cost_centers_closed",
                    "expected": True,
                    "weight": 1.0,
                },
                {
                    "name": "provisions_updated",
                    "expected": True,
                    "weight": 0.9,
                },
                {
                    "name": "budget_variance",
                    "expected": "-0.05..0.05",
                    "weight": 0.5,
                },
            ]
        },
    },
    "2024-Q4": {
        "type": "quarterly_close",
        "fiscal_year": 2024,
        "quarter": 4,
        "dod": {
            "criteria": [
                {
                    "name": "cost_centers_closed",
                    "expected": True,
                    "weight": 1.0,
                },
                {
                    "name": "provisions_updated",
                    "expected": True,
                    "weight": 0.9,
                },
                {
                    "name": "budget_variance",
                    "expected": "-0.05..0.05",
                    "weight": 0.5,
                },
                {
                    "name": "year_end_reserve_calculated",
                    "expected": True,
                    "weight": 1.0,
                },
            ]
        },
    },
    "2025-Q1": {
        "type": "quarterly_close",
        "fiscal_year": 2025,
        "quarter": 1,
        "dod": {
            "criteria": [
                {
                    "name": "cost_centers_closed",
                    "expected": True,
                    "weight": 1.0,
                },
                {
                    "name": "budget_variance",
                    "expected": "-0.10..0.10",
                    "weight": 0.5,
                },
            ]
        },
    },
}
