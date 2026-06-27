import pytest

from fetchers.file_fetcher import fetch


def test_reads_file_content(tmp_path):
    f = tmp_path / "sample.txt"
    f.write_text("hello file", encoding="utf-8")
    assert fetch(str(f)) == "hello file"


def test_custom_encoding(tmp_path):
    f = tmp_path / "latin.txt"
    f.write_bytes("café".encode("latin-1"))
    assert fetch(str(f), encoding="latin-1") == "café"


def test_file_not_found_raises():
    with pytest.raises(FileNotFoundError):
        fetch("/nonexistent/path/that/does/not/exist.txt")
