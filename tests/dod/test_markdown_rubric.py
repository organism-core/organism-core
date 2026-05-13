from __future__ import annotations

import pytest

from organism.dod import (
    EVALUATOR_LLM_JUDGE,
    Criterion,
    DoD,
    DoDEngine,
    DoDValidator,
    EvaluationContext,
    MarkdownRubricSource,
    parse_rubric,
)


# ---------- parse_rubric


def test_parse_empty_returns_no_criteria():
    assert parse_rubric("") == []


def test_parse_only_title_returns_no_criteria():
    assert parse_rubric("# Just a title\n\nSome prose.\n") == []


def test_parse_single_section_with_bullets():
    text = """\
# DCF Model Rubric

## Revenue
- Historical data spans five years
- Growth rate is stated
"""
    criteria = parse_rubric(text)
    assert len(criteria) == 2
    assert criteria[0].name.startswith("revenue.")
    assert criteria[0].expected is True
    assert criteria[0].evaluator == EVALUATOR_LLM_JUDGE
    assert criteria[0].weight == 1.0


def test_parse_multiple_sections():
    text = """\
## Section A
- Criterion A1
- Criterion A2

## Section B
- Criterion B1
"""
    criteria = parse_rubric(text)
    assert len(criteria) == 3
    sections = {c.name.split(".")[0] for c in criteria}
    assert sections == {"section_a", "section_b"}


def test_parse_extracts_weight_annotation():
    text = """\
## Section
- Important criterion [weight=2.5]
- Default criterion
- Half-weight one [weight=0.5]
"""
    criteria = parse_rubric(text)
    weights = [c.weight for c in criteria]
    assert weights == [2.5, 1.0, 0.5]


def test_parse_weight_annotation_stripped_from_name():
    text = "## Section\n- The criterion [weight=0.7]\n"
    [c] = parse_rubric(text)
    assert "weight" not in c.name
    assert "0.7" not in c.name


def test_parse_uses_default_weight_kwarg():
    text = "## Section\n- A criterion\n"
    [c] = parse_rubric(text, default_weight=0.3)
    assert c.weight == 0.3


def test_parse_ignores_non_bullet_lines():
    text = """\
## Section

Some explanatory prose that should be ignored.
- A real criterion

> Quoted text
1. Numbered list (not parsed)
- Another real criterion
"""
    criteria = parse_rubric(text)
    assert len(criteria) == 2


def test_parse_uniques_duplicate_names():
    text = """\
## Section
- Same content here
- Same content here
- Same content here
"""
    criteria = parse_rubric(text)
    names = [c.name for c in criteria]
    assert len(set(names)) == 3  # all distinct


def test_parse_empty_bullet_ignored():
    text = "## Section\n- \n- Real criterion\n"
    criteria = parse_rubric(text)
    assert len(criteria) == 1


def test_parse_no_section_uses_bare_name():
    text = "- Top-level criterion\n"
    [c] = parse_rubric(text)
    assert c.name  # non-empty
    assert "." not in c.name  # no section prefix


# ---------- MarkdownRubricSource


def test_source_satisfies_protocol():
    from organism.dod import DoDSource

    src = MarkdownRubricSource("## S\n- A criterion\n")
    assert isinstance(src, DoDSource)


def test_source_has_name():
    src = MarkdownRubricSource("## S\n- A\n")
    assert src.name == "markdown_rubric"


def test_source_contributes_criteria():
    src = MarkdownRubricSource("## Quality\n- Good output\n- Correct format\n")
    contribution = src.contribute("req", {}, DoD())
    assert len(contribution.criteria) == 2
    assert contribution.source_name == "markdown_rubric"
    assert contribution.evidence == {
        "parsed_criteria": 2,
        "contributed_criteria": 2,
    }


def test_source_confidence_delta_when_criteria_present():
    src = MarkdownRubricSource(
        "## S\n- A criterion\n", confidence_delta=0.3
    )
    contribution = src.contribute("req", {}, DoD())
    assert contribution.confidence_delta == 0.3


def test_source_empty_rubric_contributes_nothing():
    src = MarkdownRubricSource("", confidence_delta=0.5)
    contribution = src.contribute("req", {}, DoD())
    assert contribution.criteria == []
    assert contribution.confidence_delta == 0.0


def test_source_dedupes_against_existing_criteria():
    src = MarkdownRubricSource("## Sec\n- Existing one\n- Fresh one\n")
    [c1, c2] = src._criteria  # internal: get the parsed names
    dod = DoD(criteria=[Criterion(name=c1.name, expected=True)])

    contribution = src.contribute("req", {}, dod)
    contributed_names = [c.name for c in contribution.criteria]
    assert c1.name not in contributed_names  # dedup'd
    assert c2.name in contributed_names


def test_source_rejects_invalid_confidence_delta():
    with pytest.raises(ValueError, match="confidence_delta"):
        MarkdownRubricSource("## S\n- A\n", confidence_delta=1.5)


def test_source_rejects_negative_default_weight():
    with pytest.raises(ValueError, match="default_weight"):
        MarkdownRubricSource("## S\n- A\n", default_weight=-0.1)


# ---------- Integration via DoDEngine


def test_engine_integrates_markdown_rubric_source():
    rubric = """\
## Quality
- Output is well formatted
- Output is accurate

## Performance [weight=0.5]
- Output is fast [weight=0.5]
"""
    engine = DoDEngine(
        sources=[MarkdownRubricSource(rubric, confidence_delta=1.0)]
    )
    dod = engine.derive(request="r", context={})
    names = {c.name for c in dod.criteria}
    assert any("quality" in n for n in names)
    assert len(dod.criteria) == 3


def test_engine_with_rubric_runs_validator_with_llm_judge():
    """End-to-end: rubric→engine→validator. The llm_judge evaluator
    needs a callable; otherwise every criterion fails."""
    rubric = "## Section\n- Output contains a date\n- Output is in English\n"
    engine = DoDEngine(
        sources=[MarkdownRubricSource(rubric, confidence_delta=1.0)]
    )
    dod = engine.derive(request="r", context={})

    def judge(criterion, actual, result):
        # naive: "date" or "english" in actual passes
        token = "date" if "date" in criterion.name else "english"
        return token in str(actual).lower(), f"checked {token}"

    validator = DoDValidator()
    # Map names to actual content for the validator.
    name_a, name_b = sorted(c.name for c in dod.criteria)
    result_dict = {
        name_a: "the date is 2026-05-13",
        name_b: "this sentence is in English",
    }
    validation = validator.validate(
        dod, result_dict, context=EvaluationContext(llm_judge=judge)
    )
    assert validation.all_satisfied is True


def test_engine_without_llm_judge_makes_every_rubric_criterion_fail():
    """Without a wired llm_judge callable, the rubric criteria all
    fail with the 'no llm_judge callable configured' reason — explicit
    is better than silent."""
    rubric = "## S\n- A\n- B\n"
    engine = DoDEngine(
        sources=[MarkdownRubricSource(rubric, confidence_delta=1.0)]
    )
    dod = engine.derive(request="r", context={})
    validator = DoDValidator()
    name_a, name_b = sorted(c.name for c in dod.criteria)
    validation = validator.validate(
        dod, {name_a: "anything", name_b: "anything"}
    )
    assert validation.all_satisfied is False
    assert all(
        "no llm_judge callable" in r.reason
        for r in validation.criterion_results
    )
