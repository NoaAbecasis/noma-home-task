from unittest.mock import patch

import httpx
import pytest

from fetchers.content_fetcher import fetch


# --- HTTP locations ---

def test_http_url_uses_http_fetcher():
    with patch("fetchers.http_fetcher.fetch", return_value="html content") as mock_http, \
         patch("fetchers.file_fetcher.fetch") as mock_file:
        result = fetch("https://example.com", {})
    assert result == "html content"
    mock_http.assert_called_once()
    mock_file.assert_not_called()


def test_http_scheme_also_routes_to_http_fetcher():
    with patch("fetchers.http_fetcher.fetch", return_value="ok") as mock_http:
        fetch("http://example.com/file.py", {})
    mock_http.assert_called_once()


def test_http_options_forwarded():
    with patch("fetchers.http_fetcher.fetch", return_value="ok") as mock_http:
        fetch("https://example.com", {"headers": {"Authorization": "Bearer t"}, "timeout": 10})
    mock_http.assert_called_once_with(
        url="https://example.com",
        headers={"Authorization": "Bearer t"},
        timeout=10.0,
    )


# --- Filesystem locations ---

def test_file_path_uses_file_fetcher(tmp_path):
    f = tmp_path / "code.py"
    f.write_text("import os", encoding="utf-8")
    with patch("fetchers.http_fetcher.fetch") as mock_http:
        result = fetch(str(f), {})
    assert result == "import os"
    mock_http.assert_not_called()


def test_file_encoding_option_forwarded(tmp_path):
    f = tmp_path / "data.txt"
    f.write_bytes("café".encode("latin-1"))
    result = fetch(str(f), {"encoding": "latin-1"})
    assert result == "café"


def test_file_default_encoding_is_utf8(tmp_path):
    f = tmp_path / "data.txt"
    f.write_text("hello", encoding="utf-8")
    with patch("fetchers.file_fetcher.fetch", return_value="hello") as mock_file:
        fetch(str(f), {})
    mock_file.assert_called_once_with(path=str(f), encoding="utf-8")


def test_file_not_found_propagates():
    with pytest.raises(FileNotFoundError):
        fetch("/no/such/file.txt", {})
