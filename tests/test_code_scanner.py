from unittest.mock import call, patch

import pytest

from api.models import ScanRequest
from services.code_scanner import scan

PYTHON_SRC = """\
import os
import sys
from collections import defaultdict
x = 1 + 2
"""

GO_SRC = """\
import "fmt"
import "os"
import (
    "net/http"
    "encoding/json"
)
"""

JS_SRC = """\
const fs = require('fs')
const path = require('path')
import React from 'react'
import { useState } from 'react'
"""


def _req(location, patterns, options=None):
    return ScanRequest(source_type="code", location=location, patterns=patterns, options=options)


# --- HTTP source ---

def test_code_scan_via_http_returns_python_imports():
    with patch("fetchers.http_fetcher.fetch", return_value=PYTHON_SRC) as mock_fetch:
        result = scan(_req("https://raw.githubusercontent.com/org/repo/main/app.py",
                           [r"^import\s+\S+", r"^from\s+\S+\s+import\s+\S+"]))
    assert result.source_type == "code"
    assert any("import os" in m for m in result.results[0].matches)
    assert any("import sys" in m for m in result.results[0].matches)
    assert any("from collections import defaultdict" in m for m in result.results[1].matches)


def test_code_scan_via_http_passes_auth_header():
    with patch("fetchers.http_fetcher.fetch", return_value=PYTHON_SRC) as mock_fetch:
        scan(_req(
            "https://api.github.com/repos/org/repo/contents/app.py",
            [r"import\s+\S+"],
            options={"headers": {"Authorization": "Bearer mytoken"}},
        ))
    mock_fetch.assert_called_once_with(
        url="https://api.github.com/repos/org/repo/contents/app.py",
        headers={"Authorization": "Bearer mytoken"},
        timeout=30.0,
    )


def test_code_scan_via_http_passes_custom_timeout():
    with patch("fetchers.http_fetcher.fetch", return_value="import x") as mock_fetch:
        scan(_req("https://example.com/code.py", [r"import\s+\S+"], options={"timeout": 5}))
    assert mock_fetch.call_args.kwargs["timeout"] == 5.0


# --- Local file source ---

def test_code_scan_via_file_returns_go_imports(tmp_path):
    f = tmp_path / "main.go"
    f.write_text(GO_SRC, encoding="utf-8")
    result = scan(_req(str(f), [r'import\s+"[^"]+"']))
    assert 'import "fmt"' in result.results[0].matches
    assert 'import "os"' in result.results[0].matches


def test_code_scan_via_file_uses_encoding_option(tmp_path):
    f = tmp_path / "src.py"
    f.write_bytes("import café\n".encode("latin-1"))
    result = scan(_req(str(f), [r"import\s+\S+"], options={"encoding": "latin-1"}))
    assert result.results[0].matches == ["import café"]


def test_code_scan_via_file_not_found_raises():
    with pytest.raises(FileNotFoundError):
        scan(_req("/nonexistent/file.py", [r"import\s+\S+"]))


# --- JavaScript ---

def test_code_scan_js_require_and_import(tmp_path):
    f = tmp_path / "app.js"
    f.write_text(JS_SRC, encoding="utf-8")
    result = scan(_req(str(f), [r"require\('[^']+'\)", r"^import\s+.+\s+from\s+'\S+'"]))
    assert "require('fs')" in result.results[0].matches
    assert "require('path')" in result.results[0].matches
    assert any("React" in m for m in result.results[1].matches)


# --- URL detection ---

def test_http_scheme_routes_to_http_fetcher():
    with patch("fetchers.http_fetcher.fetch", return_value="import x") as mock_http, \
         patch("fetchers.file_fetcher.fetch") as mock_file:
        scan(_req("http://example.com/file.py", [r"import\s+\S+"]))
    mock_http.assert_called_once()
    mock_file.assert_not_called()


def test_file_path_routes_to_file_fetcher(tmp_path):
    f = tmp_path / "code.py"
    f.write_text("import os", encoding="utf-8")
    with patch("fetchers.http_fetcher.fetch") as mock_http:
        scan(_req(str(f), [r"import\s+\S+"]))
    mock_http.assert_not_called()
