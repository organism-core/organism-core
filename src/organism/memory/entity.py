from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml

FRONTMATTER_FENCE = "---"


@dataclass
class Entity:
    frontmatter: dict[str, Any] = field(default_factory=dict)
    body: str = ""


def parse(text: str) -> Entity:
    if not text.lstrip().startswith(FRONTMATTER_FENCE):
        return Entity(frontmatter={}, body=text)

    lines = text.split("\n")
    start_idx: int | None = None
    end_idx: int | None = None
    for i, line in enumerate(lines):
        if line.strip() == FRONTMATTER_FENCE:
            if start_idx is None:
                start_idx = i
            else:
                end_idx = i
                break

    if end_idx is None:
        return Entity(frontmatter={}, body=text)

    fm_text = "\n".join(lines[start_idx + 1 : end_idx])
    fm = yaml.safe_load(fm_text) if fm_text.strip() else {}
    if fm is None:
        fm = {}

    body_lines = lines[end_idx + 1 :]
    if body_lines and body_lines[0] == "":
        body_lines = body_lines[1:]
    body = "\n".join(body_lines)

    return Entity(frontmatter=fm, body=body)


def dump(entity: Entity) -> str:
    if not entity.frontmatter:
        return entity.body

    fm_yaml = yaml.safe_dump(
        entity.frontmatter,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
    )
    return f"{FRONTMATTER_FENCE}\n{fm_yaml}{FRONTMATTER_FENCE}\n\n{entity.body}"
