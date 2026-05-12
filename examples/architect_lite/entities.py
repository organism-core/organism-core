from __future__ import annotations

from typing import Any

ENTITIES: dict[str, dict[str, Any]] = {
    "villa-alpha-basement": {
        "type": "residential",
        "floor": "basement",
        "dod": {
            "criteria": [
                {
                    "name": "rooms_count",
                    "expected": "3..15",
                    "weight": 1.0,
                },
                {
                    "name": "parking_as_single_room",
                    "expected": True,
                    "weight": 0.5,
                },
            ]
        },
    },
    "villa-alpha-ground": {
        "type": "residential",
        "floor": "ground",
        "dod": {
            "criteria": [
                {
                    "name": "rooms_count",
                    "expected": "4..10",
                    "weight": 1.0,
                },
                {
                    "name": "rooms_with_doors",
                    "expected": ">=80%",
                    "weight": 0.8,
                },
            ]
        },
    },
    "villa-beta-attic": {
        "type": "residential",
        "floor": "attic",
        "dod": {
            "criteria": [
                {
                    "name": "rooms_count",
                    "expected": "2..5",
                    "weight": 1.0,
                },
            ]
        },
    },
}
