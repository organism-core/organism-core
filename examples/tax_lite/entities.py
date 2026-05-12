from __future__ import annotations

from typing import Any

ENTITIES: dict[str, dict[str, Any]] = {
    "client-042-2024": {
        "type": "income_tax_return",
        "fiscal_year": 2024,
        "client_type": "individual",
        "dod": {
            "criteria": [
                {
                    "name": "all_income_recorded",
                    "expected": True,
                    "weight": 1.0,
                },
                {
                    "name": "tax_class_in_range",
                    "expected": "1..6",
                    "weight": 1.0,
                },
                {
                    "name": "deductions_plausible",
                    "expected": ">=0",
                    "weight": 0.7,
                },
            ]
        },
    },
    "client-088-2024": {
        "type": "income_tax_return",
        "fiscal_year": 2024,
        "client_type": "individual",
        "dod": {
            "criteria": [
                {
                    "name": "all_income_recorded",
                    "expected": True,
                    "weight": 1.0,
                },
                {
                    "name": "tax_class_in_range",
                    "expected": "1..6",
                    "weight": 1.0,
                },
            ]
        },
    },
    "gmbh-fischer-2024": {
        "type": "corporate_tax_return",
        "fiscal_year": 2024,
        "client_type": "gmbh",
        "dod": {
            "criteria": [
                {
                    "name": "ust_id_present",
                    "expected": True,
                    "weight": 1.0,
                },
                {
                    "name": "revenue_above_threshold",
                    "expected": ">=0",
                    "weight": 0.5,
                },
            ]
        },
    },
}
