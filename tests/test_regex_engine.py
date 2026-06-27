import re

import pytest

from services.regex_engine import apply_patterns


def test_single_pattern_matches():
    results = apply_patterns("hello world", [r"\b\w+\b"])
    assert results[0].matches == ["hello", "world"]


def test_no_matches():
    results = apply_patterns("hello", [r"\d+"])
    assert results[0].matches == []


def test_multiple_patterns_independent():
    results = apply_patterns("hello 123", [r"\d+", r"[a-z]+"])
    assert results[0].pattern == r"\d+"
    assert results[0].matches == ["123"]
    assert results[1].pattern == r"[a-z]+"
    assert results[1].matches == ["hello"]


def test_full_match_returned_not_capture_group():
    # group(0) is the full match, not the captured group inside parentheses
    results = apply_patterns('href="https://example.com"', [r'href="([^"]+)"'])
    assert results[0].matches == ['href="https://example.com"']


def test_invalid_pattern_raises_re_error():
    with pytest.raises(re.error):
        apply_patterns("content", ["[invalid"])


def test_empty_content_returns_no_matches():
    results = apply_patterns("", [r"\w+"])
    assert results[0].matches == []
