from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any


@dataclass
class Provenance:
    author: str
    timestamp: datetime
    source: str = ""
    confidence: float = 1.0
    validated_by_user: bool = False

    def __post_init__(self) -> None:
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(
                f"confidence must be in [0, 1], got {self.confidence}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "author": self.author,
            "timestamp": self.timestamp.isoformat(),
            "source": self.source,
            "confidence": self.confidence,
            "validated_by_user": self.validated_by_user,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Provenance:
        return cls(
            author=data["author"],
            timestamp=_parse_datetime(data["timestamp"]),
            source=data.get("source", ""),
            confidence=float(data.get("confidence", 1.0)),
            validated_by_user=bool(data.get("validated_by_user", False)),
        )

    @classmethod
    def now(
        cls,
        author: str,
        *,
        source: str = "",
        confidence: float = 1.0,
        validated_by_user: bool = False,
    ) -> Provenance:
        return cls(
            author=author,
            timestamp=datetime.now(timezone.utc),
            source=source,
            confidence=confidence,
            validated_by_user=validated_by_user,
        )


def _parse_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)
