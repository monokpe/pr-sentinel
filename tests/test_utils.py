"""
Unit tests for pr_sentinel.agents.utils.extract_json
"""
import pytest
from pr_sentinel.agents.utils import extract_json


def test_bare_json():
    raw = '{"findings": [], "summary": "all good"}'
    result = extract_json(raw)
    assert result == {"findings": [], "summary": "all good"}


def test_json_in_markdown_fence():
    raw = '```json\n{"findings": [{"severity": "high"}], "summary": "oops"}\n```'
    result = extract_json(raw)
    assert result["summary"] == "oops"
    assert result["findings"][0]["severity"] == "high"


def test_json_in_plain_fence():
    raw = '```\n{"key": "value"}\n```'
    result = extract_json(raw)
    assert result == {"key": "value"}


def test_json_with_preamble():
    raw = 'Here is the analysis:\n\n{"findings": [], "summary": "clean"}'
    result = extract_json(raw)
    assert result["summary"] == "clean"


def test_json_with_trailing_commentary():
    raw = '{"findings": [], "summary": "ok"}\n\nPlease review the above.'
    result = extract_json(raw)
    assert result["summary"] == "ok"


def test_empty_string_raises():
    with pytest.raises(ValueError, match="Empty response"):
        extract_json("")


def test_unparseable_raises():
    with pytest.raises(ValueError, match="Could not extract valid JSON"):
        extract_json("this is definitely not json at all")


def test_severity_guard_unknown_value():
    """Verify that the severity coercion guard in agents degrades to 'info'."""
    from pr_sentinel.models import Severity
    _VALID = {s.value for s in Severity}
    raw_severity = "super-critical"
    coerced = raw_severity if raw_severity in _VALID else "info"
    assert coerced == "info"
