from typing import Any

from organism.dod import (
    DoD,
    DoDSource,
    UserClarificationSource,
)


def test_user_clarification_satisfies_protocol():
    assert isinstance(UserClarificationSource(), DoDSource)


def test_default_questions_when_no_prior_clarification():
    ucs = UserClarificationSource()
    contribution = ucs.contribute(request="any", context={}, current=DoD())
    assert contribution.source_name == "user_clarification"
    assert len(contribution.clarifications) == 1
    assert contribution.confidence_delta == 0.0
    assert contribution.evidence == {"trigger": "exhausted_upstream_sources"}


def test_no_questions_when_prior_clarification_exists():
    ucs = UserClarificationSource()
    current = DoD(clarification_needed=["earlier_question"])
    contribution = ucs.contribute(request="any", context={}, current=current)
    assert contribution.clarifications == []
    assert contribution.evidence == {}


def test_custom_question_generator_used():
    def custom(
        request: Any, ctx: dict[str, Any], current: DoD
    ) -> list[str]:
        return [f"specific question about {request}"]

    ucs = UserClarificationSource(generate_questions=custom)
    contribution = ucs.contribute(
        request="task_x", context={}, current=DoD()
    )
    assert contribution.clarifications == ["specific question about task_x"]


def test_terminal_source_never_adds_confidence():
    ucs = UserClarificationSource()
    contribution = ucs.contribute(request="any", context={}, current=DoD())
    assert contribution.confidence_delta == 0.0


def test_custom_generator_can_return_empty_list():
    def custom(
        request: Any, ctx: dict[str, Any], current: DoD
    ) -> list[str]:
        return []

    ucs = UserClarificationSource(generate_questions=custom)
    contribution = ucs.contribute(request="any", context={}, current=DoD())
    assert contribution.clarifications == []
    assert contribution.evidence == {}
