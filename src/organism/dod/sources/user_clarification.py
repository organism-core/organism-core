from __future__ import annotations

from typing import Any, Callable

from organism.dod.types import DoD, SourceContribution


def _default_questions(
    request: Any, context: dict[str, Any], current: DoD
) -> list[str]:
    if current.clarification_needed:
        return []
    return [
        "DoD could not be derived from upstream sources — user input required"
    ]


class UserClarificationSource:
    name = "user_clarification"

    def __init__(
        self,
        generate_questions: Callable[
            [Any, dict[str, Any], DoD], list[str]
        ]
        | None = None,
    ) -> None:
        self._generate = generate_questions or _default_questions

    def contribute(
        self,
        request: Any,
        context: dict[str, Any],
        current: DoD,
    ) -> SourceContribution:
        questions = self._generate(request, context, current)
        return SourceContribution(
            source_name=self.name,
            clarifications=questions,
            evidence=(
                {"trigger": "exhausted_upstream_sources"} if questions else {}
            ),
        )
