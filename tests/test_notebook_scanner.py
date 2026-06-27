import json
from unittest.mock import patch

import pytest

from api.models import ScanRequest
from services.notebook_scanner import scan

NOTEBOOK = {
    "nbformat": 4,
    "cells": [
        {"cell_type": "code", "source": ["import os\n", "import requests\n"]},
        {"cell_type": "markdown", "source": ["# Analysis\n"]},
        {"cell_type": "code", "source": ["import subprocess\n", "subprocess.run(['ls'])\n"]},
    ],
}
RAW = json.dumps(NOTEBOOK)


def _req(location, patterns, options=None):
    return ScanRequest(source_type="notebook", location=location, patterns=patterns, options=options)


def test_finds_imports_across_all_code_cells():
    with patch("fetchers.content_fetcher.fetch", return_value=RAW):
        result = scan(_req("https://example.com/nb.ipynb", [r"^import\s+\S+"]))
    matches = result.results[0].matches
    assert "import os" in matches
    assert "import requests" in matches
    assert "import subprocess" in matches


def test_markdown_content_not_matched():
    with patch("fetchers.content_fetcher.fetch", return_value=RAW):
        result = scan(_req("https://example.com/nb.ipynb", [r"Analysis"]))
    assert result.results[0].matches == []


def test_scan_from_local_file(tmp_path):
    f = tmp_path / "analysis.ipynb"
    f.write_text(RAW, encoding="utf-8")
    result = scan(_req(str(f), [r"^import\s+\S+"]))
    assert "import subprocess" in result.results[0].matches


def test_scan_from_local_file_with_encoding(tmp_path):
    nb = {"nbformat": 4, "cells": [{"cell_type": "code", "source": ["import café\n"]}]}
    f = tmp_path / "notebook.ipynb"
    f.write_bytes(json.dumps(nb).encode("latin-1"))
    result = scan(_req(str(f), [r"import\s+\S+"], options={"encoding": "latin-1"}))
    assert result.results[0].matches == ["import café"]


def test_multiple_patterns():
    with patch("fetchers.content_fetcher.fetch", return_value=RAW):
        result = scan(_req(
            "https://example.com/nb.ipynb",
            [r"^import\s+\S+", r"subprocess\.run"],
        ))
    assert len(result.results) == 2
    assert result.results[1].matches == ["subprocess.run"]


def test_http_auth_header_forwarded():
    with patch("fetchers.content_fetcher.fetch", return_value=RAW) as mock_fetch:
        scan(_req(
            "https://example.com/nb.ipynb",
            [r"import"],
            options={"headers": {"Authorization": "Bearer secret"}},
        ))
    mock_fetch.assert_called_once_with(
        "https://example.com/nb.ipynb",
        {"headers": {"Authorization": "Bearer secret"}},
    )


def test_invalid_json_raises():
    with patch("fetchers.content_fetcher.fetch", return_value="not json {{"):
        with pytest.raises(Exception):
            scan(_req("https://example.com/nb.ipynb", [r"import"]))


def test_response_fields():
    with patch("fetchers.content_fetcher.fetch", return_value=RAW):
        result = scan(_req("https://example.com/nb.ipynb", [r"import"]))
    assert result.source_type == "notebook"
    assert result.location == "https://example.com/nb.ipynb"
