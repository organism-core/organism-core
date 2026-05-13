"""Markdown rubric parser + DoDSource.

Anthropic's Outcomes feature (Claude Managed Agents, public beta, May
2026) accepts rubrics as markdown documents with section headings plus
bulleted criteria. ``MarkdownRubricSource`` adopts the same format so
consumers with existing Outcomes-style rubrics can wire them up without
rewriting to YAML/dataclass form.

Format:

    # Title (ignored)

    ## Section name

    - Criterion description sentence
    - Another criterion with explicit weight [weight=0.5]
    - Yet another criterion

    ## Another section

    - Final criterion [weight=2.0]

Each `- bullet` becomes a `Criterion`:
- ``expected = True`` (presence-style — the grader judges whether the
  criterion is met)
- ``evaluator = llm_judge`` (qualitative — consumers must wire an
  ``llm_judge`` callable via ``DoDValidator``'s ``EvaluationContext``)
- ``weight = default_weight`` unless an explicit ``[weight=N]``
  annotation appears in the bullet text (then that wins; the
  annotation is stripped from the criterion description)
- ``name`` is a slug derived from the section + bullet description,
  uniqued by the engine's merge step

`#`-level-1 headings (document titles) are ignored. Lines that are not
`##` headings or `-` bullets are ignored entirely — explanatory prose,
blank lines, and code fences pass through harmlessly.
"""

from __future__ import annotations

import re
from typing import Any

from organism.dod.types import (
    EVALUATOR_LLM_JUDGE,
    Criterion,
    DoD,
    SourceContribution,
)

_WEIGHT_RE = re.compile(r"\[weight=([0-9]+(?:\.[0-9]+)?)\]")
_SLUG_RE = re.compile(r"[^a-z0-9_]+")
_NAME_MAX_TAIL = 40


def parse_rubric(
    text: str, *, default_weight: float = 1.0
) -> list[Criterion]:
    """Parse a markdown rubric string into a list of ``Criterion``."""
    criteria: list[Criterion] = []
    seen_names: set[str] = set()
    current_section = ""
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if line.startswith("## "):
            current_section = line[3:].strip()
            continue
        if line.startswith("- "):
            content = line[2:].strip()
            if not content:
                continue
            weight = default_weight
            match = _WEIGHT_RE.search(content)
            if match:
                weight = float(match.group(1))
                content = _WEIGHT_RE.sub("", content).strip()
            name = _criterion_name(current_section, content, seen_names)
            seen_names.add(name)
            criteria.append(
                Criterion(
                    name=name,
                    expected=True,
                    weight=weight,
                    evaluator=EVALUATOR_LLM_JUDGE,
                )
            )
    return criteria


def _criterion_name(
    section: str, content: str, seen: set[str]
) -> str:
    section_slug = _slug(section)
    content_slug = _slug(content)[:_NAME_MAX_TAIL].strip("_")
    base = (
        f"{section_slug}.{content_slug}" if section_slug else content_slug
    )
    if not base:
        base = "criterion"
    candidate = base
    suffix = 2
    while candidate in seen:
        candidate = f"{base}_{suffix}"
        suffix += 1
    return candidate


def _slug(s: str) -> str:
    return _SLUG_RE.sub("_", s.lower()).strip("_")


class MarkdownRubricSource:
    """Contributes criteria parsed from a markdown rubric string.

    Consumers can construct this source with a static rubric, or build
    it dynamically (subclass and override the parser, or rebuild the
    source per request) when the rubric is request-dependent.

    The contributed criteria carry ``evaluator='llm_judge'`` —
    consumers must wire an ``llm_judge`` callable via the validator's
    ``EvaluationContext``; otherwise every criterion fails with the
    "no llm_judge callable configured" reason.
    """

    name = "markdown_rubric"

    def __init__(
        self,
        rubric: str,
        *,
        confidence_delta: float = 0.5,
        default_weight: float = 1.0,
    ) -> None:
        if not 0.0 <= confidence_delta <= 1.0:
            raise ValueError(
                "confidence_delta must be in [0, 1], "
                f"got {confidence_delta}"
            )
        if default_weight < 0.0:
            raise ValueError(
                f"default_weight must be >= 0, got {default_weight}"
            )
        self._criteria = parse_rubric(rubric, default_weight=default_weight)
        self._confidence_delta = (
            confidence_delta if self._criteria else 0.0
        )

    def contribute(
        self,
        request: Any,
        context: dict[str, Any],
        current: DoD,
    ) -> SourceContribution:
        existing = {c.name for c in current.criteria}
        new_criteria = [
            c for c in self._criteria if c.name not in existing
        ]
        evidence: dict[str, Any] = {
            "parsed_criteria": len(self._criteria),
            "contributed_criteria": len(new_criteria),
        }
        return SourceContribution(
            source_name=self.name,
            criteria=new_criteria,
            confidence_delta=(
                self._confidence_delta if new_criteria else 0.0
            ),
            evidence=evidence,
        )
