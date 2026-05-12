from __future__ import annotations

from datetime import datetime, timezone

import pytest

from organism.provenance import Provenance


def test_basic_construction():
    p = Provenance(
        author="ef",
        timestamp=datetime(2026, 5, 9, 10, 0, 0, tzinfo=timezone.utc),
    )
    assert p.author == "ef"
    assert p.source == ""
    assert p.confidence == 1.0
    assert p.validated_by_user is False


def test_full_construction():
    p = Provenance(
        author="ef",
        timestamp=datetime(2026, 5, 9, 10, 0, 0, tzinfo=timezone.utc),
        source="some doc",
        confidence=0.85,
        validated_by_user=True,
    )
    assert p.confidence == 0.85
    assert p.validated_by_user is True


def test_confidence_above_one_raises():
    with pytest.raises(ValueError, match="confidence must be in"):
        Provenance(
            author="ef",
            timestamp=datetime(2026, 5, 9, 10, 0, 0, tzinfo=timezone.utc),
            confidence=1.5,
        )


def test_confidence_negative_raises():
    with pytest.raises(ValueError, match="confidence must be in"):
        Provenance(
            author="ef",
            timestamp=datetime(2026, 5, 9, 10, 0, 0, tzinfo=timezone.utc),
            confidence=-0.1,
        )


def test_confidence_at_boundaries_ok():
    Provenance(
        author="ef",
        timestamp=datetime(2026, 5, 9, 10, 0, 0, tzinfo=timezone.utc),
        confidence=0.0,
    )
    Provenance(
        author="ef",
        timestamp=datetime(2026, 5, 9, 10, 0, 0, tzinfo=timezone.utc),
        confidence=1.0,
    )


def test_to_dict():
    p = Provenance(
        author="ef",
        timestamp=datetime(2026, 5, 9, 10, 0, 0, tzinfo=timezone.utc),
        source="doc",
        confidence=0.85,
        validated_by_user=True,
    )
    assert p.to_dict() == {
        "author": "ef",
        "timestamp": "2026-05-09T10:00:00+00:00",
        "source": "doc",
        "confidence": 0.85,
        "validated_by_user": True,
    }


def test_round_trip():
    original = Provenance(
        author="ef",
        timestamp=datetime(2026, 5, 9, 10, 0, 0, tzinfo=timezone.utc),
        source="doc",
        confidence=0.85,
        validated_by_user=True,
    )
    assert Provenance.from_dict(original.to_dict()) == original


def test_from_dict_accepts_datetime_object():
    p = Provenance.from_dict(
        {
            "author": "ef",
            "timestamp": datetime(
                2026, 5, 9, 10, 0, 0, tzinfo=timezone.utc
            ),
        }
    )
    assert p.timestamp == datetime(
        2026, 5, 9, 10, 0, 0, tzinfo=timezone.utc
    )


def test_from_dict_lenient_on_missing_optional_fields():
    p = Provenance.from_dict(
        {"author": "ef", "timestamp": "2026-05-09T10:00:00+00:00"}
    )
    assert p.source == ""
    assert p.confidence == 1.0
    assert p.validated_by_user is False


def test_now_creates_with_current_time():
    p = Provenance.now("ef")
    delta = (datetime.now(timezone.utc) - p.timestamp).total_seconds()
    assert 0 <= delta < 5
    assert p.author == "ef"


def test_now_uses_utc_timezone():
    p = Provenance.now("ef")
    assert p.timestamp.tzinfo is timezone.utc


def test_now_with_keyword_args():
    p = Provenance.now(
        "ef",
        source="doc",
        confidence=0.5,
        validated_by_user=True,
    )
    assert p.author == "ef"
    assert p.source == "doc"
    assert p.confidence == 0.5
    assert p.validated_by_user is True
