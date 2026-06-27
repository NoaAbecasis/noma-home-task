"""
Input validation tests for POST /scan.

These tests exercise Pydantic model validation (422) and the route-level
error mapping for bad regex patterns and unsupported source types.
They do not test fetch or parse behaviour — that lives in test_api.py.
"""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

VALID = {
    "source_type": "url",
    "location": "https://example.com",
    "patterns": [r"\w+"],
}


def post(body: dict) -> int:
    return client.post("/scan", json=body).status_code


def without(key: str) -> dict:
    return {k: v for k, v in VALID.items() if k != key}


def with_field(**kwargs) -> dict:
    return {**VALID, **kwargs}


# ---------------------------------------------------------------------------
# Missing required fields
# ---------------------------------------------------------------------------

def test_missing_source_type_returns_422():
    assert post(without("source_type")) == 422


def test_missing_location_returns_422():
    assert post(without("location")) == 422


def test_missing_patterns_returns_422():
    assert post(without("patterns")) == 422


def test_empty_body_returns_422():
    assert post({}) == 422


# ---------------------------------------------------------------------------
# source_type
# ---------------------------------------------------------------------------

def test_unknown_source_type_returns_422():
    assert post(with_field(source_type="xml")) == 422


def test_unknown_source_type_zip_returns_422():
    assert post(with_field(source_type="zip")) == 422


def test_empty_source_type_returns_422():
    assert post(with_field(source_type="")) == 422


def test_null_source_type_returns_422():
    assert post(with_field(source_type=None)) == 422


def test_numeric_source_type_returns_422():
    assert post(with_field(source_type=1)) == 422


# ---------------------------------------------------------------------------
# location
# ---------------------------------------------------------------------------

def test_empty_location_returns_422():
    assert post(with_field(location="")) == 422


def test_null_location_returns_422():
    assert post(with_field(location=None)) == 422


# ---------------------------------------------------------------------------
# patterns
# ---------------------------------------------------------------------------

def test_empty_patterns_list_returns_422():
    assert post(with_field(patterns=[])) == 422


def test_null_patterns_returns_422():
    assert post(with_field(patterns=None)) == 422


def test_patterns_as_bare_string_returns_422():
    assert post(with_field(patterns=r"\w+")) == 422


def test_patterns_list_containing_empty_string_returns_422():
    assert post(with_field(patterns=[""])) == 422


def test_patterns_list_containing_empty_string_among_valid_returns_422():
    assert post(with_field(patterns=[r"\w+", ""])) == 422


def test_invalid_regex_returns_422():
    with patch("fetchers.http_fetcher.fetch", return_value="content"):
        assert post(with_field(patterns=["[invalid"])) == 422


def test_multiple_invalid_regex_returns_422():
    with patch("fetchers.http_fetcher.fetch", return_value="content"):
        assert post(with_field(patterns=["[bad", "(?P<"])) == 422


# ---------------------------------------------------------------------------
# options
# ---------------------------------------------------------------------------

def test_options_as_list_returns_422():
    assert post(with_field(options=["Authorization", "Bearer tok"])) == 422


def test_options_as_string_returns_422():
    assert post(with_field(options="Authorization: Bearer tok")) == 422


def test_options_as_integer_returns_422():
    assert post(with_field(options=42)) == 422


# ---------------------------------------------------------------------------
# Valid edge cases that must NOT be rejected
# ---------------------------------------------------------------------------

def test_options_null_is_accepted():
    with patch("fetchers.http_fetcher.fetch", return_value="hello"):
        assert client.post("/scan", json=with_field(options=None)).status_code == 200


def test_options_empty_dict_is_accepted():
    with patch("fetchers.http_fetcher.fetch", return_value="hello"):
        assert client.post("/scan", json=with_field(options={})).status_code == 200


def test_all_source_types_are_accepted(tmp_path):
    nb = '{"nbformat":4,"cells":[{"cell_type":"code","source":["x=1"]}]}'
    local_file = tmp_path / "f.txt"
    local_file.write_text("hello", encoding="utf-8")
    local_nb = tmp_path / "nb.ipynb"
    local_nb.write_text(nb, encoding="utf-8")

    cases = [
        with_field(source_type="url",      location="https://example.com"),
        with_field(source_type="code",     location="https://example.com"),
        with_field(source_type="file",     location=str(local_file)),
        with_field(source_type="notebook", location=str(local_nb)),
    ]
    with patch("fetchers.http_fetcher.fetch", return_value="hello"):
        for body in cases:
            resp = client.post("/scan", json=body)
            assert resp.status_code == 200, f"Expected 200 for source_type={body['source_type']!r}, got {resp.status_code}: {resp.json()}"


def test_multiple_valid_patterns_accepted():
    with patch("fetchers.http_fetcher.fetch", return_value="import os"):
        resp = client.post("/scan", json=with_field(patterns=[r"\w+", r"\d+", r"import"]))
    assert resp.status_code == 200
    assert len(resp.json()["results"]) == 3
