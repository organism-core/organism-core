from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

TOOL_TYPE_QUERIER = "querier"
TOOL_TYPE_EFFECTOR = "effector"
TOOL_TYPE_UNSET = ""
TOOL_TYPES = frozenset(
    {TOOL_TYPE_QUERIER, TOOL_TYPE_EFFECTOR, TOOL_TYPE_UNSET}
)


@dataclass
class RegisteredTool:
    name: str
    kinds: list[str] = field(default_factory=list)
    description: str = ""
    tool_type: str = TOOL_TYPE_UNSET

    def __post_init__(self) -> None:
        if self.tool_type not in TOOL_TYPES:
            raise ValueError(
                f"tool_type must be one of {sorted(TOOL_TYPES)} or empty, "
                f"got {self.tool_type!r}"
            )

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "name": self.name,
            "kinds": list(self.kinds),
            "description": self.description,
        }
        # Omit default empty tool_type for backward-compat with stored data.
        if self.tool_type != TOOL_TYPE_UNSET:
            d["tool_type"] = self.tool_type
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RegisteredTool:
        return cls(
            name=data["name"],
            kinds=list(data.get("kinds") or []),
            description=data.get("description", ""),
            tool_type=data.get("tool_type", TOOL_TYPE_UNSET),
        )


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(
        self,
        *,
        name: str,
        kinds: list[str],
        description: str = "",
        tool_type: str = TOOL_TYPE_UNSET,
    ) -> RegisteredTool:
        if name in self._tools:
            raise ValueError(f"Tool {name!r} already registered")
        tool = RegisteredTool(
            name=name,
            kinds=list(kinds),
            description=description,
            tool_type=tool_type,
        )
        self._tools[name] = tool
        return tool

    def unregister(self, name: str) -> None:
        if name not in self._tools:
            raise KeyError(f"Tool {name!r} not registered")
        del self._tools[name]

    def get(self, name: str) -> RegisteredTool:
        if name not in self._tools:
            raise KeyError(f"Tool {name!r} not registered")
        return self._tools[name]

    def has(self, name: str) -> bool:
        return name in self._tools

    def list(
        self, *, tool_type: str | None = None
    ) -> list[RegisteredTool]:
        items = sorted(self._tools.values(), key=lambda t: t.name)
        if tool_type is None:
            return items
        if tool_type not in TOOL_TYPES:
            raise ValueError(
                f"tool_type filter must be one of {sorted(TOOL_TYPES)}, "
                f"got {tool_type!r}"
            )
        return [t for t in items if t.tool_type == tool_type]

    def find_for_kind(
        self, kind: str, *, tool_type: str | None = None
    ) -> list[RegisteredTool]:
        candidates = self.list(tool_type=tool_type)
        return [t for t in candidates if kind in t.kinds]
