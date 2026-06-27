import json
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

HTML = '<a href="https://good.com">ok</a> <a href="https://evil.com">bad</a>'
HREF_PATTERN = r'href="(https?://[^"]+)"'


def test_scan_url_returns_all_matches():
    with patch("fetchers.http_fetcher.fetch", return_value=HTML):
        resp = client.post("/scan", json={
            "source_type": "url",
            "location": "https://fake.com",
            "patterns": [HREF_PATTERN],
        })
    assert resp.status_code == 200
    data = resp.json()
    assert data["source_type"] == "url"
    assert data["location"] == "https://fake.com"
    matches = data["results"][0]["matches"]
    assert 'href="https://good.com"' in matches
    assert 'href="https://evil.com"' in matches


def test_scan_url_no_matches():
    with patch("fetchers.http_fetcher.fetch", return_value="<p>no links here</p>"):
        resp = client.post("/scan", json={
            "source_type": "url",
            "location": "https://fake.com",
            "patterns": [HREF_PATTERN],
        })
    assert resp.status_code == 200
    assert resp.json()["results"][0]["matches"] == []


def test_scan_file_returns_matches(tmp_path):
    f = tmp_path / "data.txt"
    f.write_text("foo bar baz 123", encoding="utf-8")
    resp = client.post("/scan", json={
        "source_type": "file",
        "location": str(f),
        "patterns": [r"\d+"],
    })
    assert resp.status_code == 200
    assert resp.json()["results"][0]["matches"] == ["123"]


def test_scan_file_with_encoding_option(tmp_path):
    f = tmp_path / "data.txt"
    f.write_bytes("café 42".encode("latin-1"))
    resp = client.post("/scan", json={
        "source_type": "file",
        "location": str(f),
        "patterns": [r"\d+"],
        "options": {"encoding": "latin-1"},
    })
    assert resp.status_code == 200
    assert resp.json()["results"][0]["matches"] == ["42"]


def test_multiple_patterns_in_one_request():
    with patch("fetchers.http_fetcher.fetch", return_value=HTML):
        resp = client.post("/scan", json={
            "source_type": "url",
            "location": "https://fake.com",
            "patterns": [HREF_PATTERN, r"https://evil\.com"],
        })
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 2
    assert results[1]["matches"] == ["https://evil.com"]


def test_invalid_regex_returns_422():
    with patch("fetchers.http_fetcher.fetch", return_value="content"):
        resp = client.post("/scan", json={
            "source_type": "url",
            "location": "https://fake.com",
            "patterns": ["[invalid"],
        })
    assert resp.status_code == 422


def test_empty_patterns_list_returns_422():
    resp = client.post("/scan", json={
        "source_type": "url",
        "location": "https://fake.com",
        "patterns": [],
    })
    assert resp.status_code == 422


def test_url_fetch_error_returns_502():
    with patch("fetchers.http_fetcher.fetch", side_effect=httpx.RequestError(
        "connection failed", request=httpx.Request("GET", "https://fake.com")
    )):
        resp = client.post("/scan", json={
            "source_type": "url",
            "location": "https://fake.com",
            "patterns": [r"\w+"],
        })
    assert resp.status_code == 502


def test_url_http_status_error_returns_502():
    mock_request = httpx.Request("GET", "https://fake.com")
    mock_response = httpx.Response(403, request=mock_request)
    with patch("fetchers.http_fetcher.fetch", side_effect=httpx.HTTPStatusError(
        "403", request=mock_request, response=mock_response
    )):
        resp = client.post("/scan", json={
            "source_type": "url",
            "location": "https://fake.com",
            "patterns": [r"\w+"],
        })
    assert resp.status_code == 502


def test_file_not_found_returns_400():
    resp = client.post("/scan", json={
        "source_type": "file",
        "location": "/nonexistent/file.txt",
        "patterns": [r"\w+"],
    })
    assert resp.status_code == 400


def test_options_passed_to_http_fetcher():
    with patch("fetchers.http_fetcher.fetch", return_value="ok") as mock_fetch:
        client.post("/scan", json={
            "source_type": "url",
            "location": "https://fake.com",
            "patterns": [r"\w+"],
            "options": {"headers": {"X-Custom": "value"}, "timeout": 10},
        })
    mock_fetch.assert_called_once_with(
        url="https://fake.com",
        headers={"X-Custom": "value"},
        timeout=10.0,
    )


# --- code source type ---

PYTHON_CODE = "import os\nimport sys\nfrom pathlib import Path\nx = 1\n"


def test_scan_code_via_http_returns_imports():
    with patch("fetchers.http_fetcher.fetch", return_value=PYTHON_CODE):
        resp = client.post("/scan", json={
            "source_type": "code",
            "location": "https://raw.githubusercontent.com/org/repo/main/app.py",
            "patterns": [r"^import\s+\S+"],
        })
    assert resp.status_code == 200
    matches = resp.json()["results"][0]["matches"]
    assert "import os" in matches
    assert "import sys" in matches


def test_scan_code_via_http_with_auth_header():
    with patch("fetchers.http_fetcher.fetch", return_value=PYTHON_CODE) as mock_fetch:
        resp = client.post("/scan", json={
            "source_type": "code",
            "location": "https://api.github.com/repos/org/repo/contents/app.py",
            "patterns": [r"import\s+\S+"],
            "options": {"headers": {"Authorization": "Bearer secret"}},
        })
    assert resp.status_code == 200
    mock_fetch.assert_called_once_with(
        url="https://api.github.com/repos/org/repo/contents/app.py",
        headers={"Authorization": "Bearer secret"},
        timeout=30.0,
    )


def test_scan_code_via_local_file(tmp_path):
    f = tmp_path / "app.py"
    f.write_text(PYTHON_CODE, encoding="utf-8")
    resp = client.post("/scan", json={
        "source_type": "code",
        "location": str(f),
        "patterns": [r"^from\s+\S+\s+import\s+\S+"],
    })
    assert resp.status_code == 200
    assert resp.json()["results"][0]["matches"] == ["from pathlib import Path"]


# --- notebook source type ---

NOTEBOOK = {
    "nbformat": 4,
    "cells": [
        {"cell_type": "code", "source": ["import os\n", "import requests\n"]},
        {"cell_type": "markdown", "source": ["# Notes\n"]},
        {"cell_type": "code", "source": ["import subprocess\n"]},
    ],
}


def test_scan_notebook_via_http_returns_code_cell_imports():
    with patch("fetchers.http_fetcher.fetch", return_value=json.dumps(NOTEBOOK)):
        resp = client.post("/scan", json={
            "source_type": "notebook",
            "location": "https://raw.githubusercontent.com/org/repo/main/analysis.ipynb",
            "patterns": [r"^import\s+\S+"],
        })
    assert resp.status_code == 200
    matches = resp.json()["results"][0]["matches"]
    assert "import os" in matches
    assert "import requests" in matches
    assert "import subprocess" in matches


def test_scan_notebook_excludes_markdown():
    with patch("fetchers.http_fetcher.fetch", return_value=json.dumps(NOTEBOOK)):
        resp = client.post("/scan", json={
            "source_type": "notebook",
            "location": "https://example.com/nb.ipynb",
            "patterns": [r"Notes"],
        })
    assert resp.status_code == 200
    assert resp.json()["results"][0]["matches"] == []


def test_scan_notebook_from_local_file(tmp_path):
    f = tmp_path / "nb.ipynb"
    f.write_text(json.dumps(NOTEBOOK), encoding="utf-8")
    resp = client.post("/scan", json={
        "source_type": "notebook",
        "location": str(f),
        "patterns": [r"^import\s+\S+"],
    })
    assert resp.status_code == 200
    assert "import subprocess" in resp.json()["results"][0]["matches"]


def test_scan_notebook_invalid_json_returns_422():
    with patch("fetchers.http_fetcher.fetch", return_value="not valid json {{"):
        resp = client.post("/scan", json={
            "source_type": "notebook",
            "location": "https://example.com/nb.ipynb",
            "patterns": [r"import"],
        })
    assert resp.status_code == 422


def test_scan_notebook_with_auth_header():
    with patch("fetchers.http_fetcher.fetch", return_value=json.dumps(NOTEBOOK)) as mock_fetch:
        resp = client.post("/scan", json={
            "source_type": "notebook",
            "location": "https://example.com/nb.ipynb",
            "patterns": [r"import"],
            "options": {"headers": {"Authorization": "Bearer tok"}},
        })
    assert resp.status_code == 200
    mock_fetch.assert_called_once_with(
        url="https://example.com/nb.ipynb",
        headers={"Authorization": "Bearer tok"},
        timeout=30.0,
    )
