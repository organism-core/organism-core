from __future__ import annotations

import pytest

from organism.query import QueryRunnerSettings


def test_default_settings():
    s = QueryRunnerSettings()
    assert s.record_traces is True
    assert s.truncate_request_repr == 200
    assert s.truncate_result_repr == 500
    assert s.emit_events is False


def test_truncate_request_repr_min():
    with pytest.raises(ValueError, match="truncate_request_repr"):
        QueryRunnerSettings(truncate_request_repr=8)


def test_truncate_result_repr_min():
    with pytest.raises(ValueError, match="truncate_result_repr"):
        QueryRunnerSettings(truncate_result_repr=4)
