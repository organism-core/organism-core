from organism.memory import Entity, dump, parse


def test_parse_with_frontmatter():
    text = """---
name: alpha
status: active
tags:
  - x
  - y
---

# Hello

Body line one.
Body line two."""
    e = parse(text)
    assert e.frontmatter == {
        "name": "alpha",
        "status": "active",
        "tags": ["x", "y"],
    }
    assert e.body == "# Hello\n\nBody line one.\nBody line two."


def test_parse_body_only():
    text = "no frontmatter here\njust body"
    e = parse(text)
    assert e.frontmatter == {}
    assert e.body == text


def test_parse_empty_frontmatter():
    text = "---\n---\n\nbody"
    e = parse(text)
    assert e.frontmatter == {}
    assert e.body == "body"


def test_parse_unclosed_frontmatter_treated_as_body():
    text = "---\nname: alpha\nbody without close"
    e = parse(text)
    assert e.frontmatter == {}
    assert e.body == text


def test_dump_with_frontmatter():
    e = Entity(frontmatter={"name": "alpha"}, body="# Title\n\ntext")
    out = dump(e)
    assert out.startswith("---\n")
    assert "name: alpha" in out
    assert out.endswith("# Title\n\ntext")


def test_dump_body_only_when_frontmatter_empty():
    e = Entity(frontmatter={}, body="just text")
    assert dump(e) == "just text"


def test_round_trip_preserves_frontmatter_and_body():
    original = Entity(
        frontmatter={"id": "42", "tags": ["a", "b"], "owner": {"name": "X"}},
        body="# Heading\n\nParagraph.",
    )
    parsed = parse(dump(original))
    assert parsed.frontmatter == original.frontmatter
    assert parsed.body == original.body


def test_round_trip_empty_body():
    original = Entity(frontmatter={"id": "1"}, body="")
    parsed = parse(dump(original))
    assert parsed.frontmatter == original.frontmatter
    assert parsed.body == ""


def test_schema_free_arbitrary_fields_accepted():
    text = """---
totally_new_field: 123
nested:
  arbitrary: value
---
body"""
    e = parse(text)
    assert e.frontmatter["totally_new_field"] == 123
    assert e.frontmatter["nested"]["arbitrary"] == "value"
