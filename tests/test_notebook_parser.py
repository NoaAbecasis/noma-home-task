import json

import pytest

from parsers.notebook_parser import extract_cell_sources

NOTEBOOK = {
    "nbformat": 4,
    "cells": [
        {"cell_type": "code", "source": ["import os\n", "import sys\n"]},
        {"cell_type": "markdown", "source": ["# Title\n", "Some text.\n"]},
        {"cell_type": "code", "source": ["x = 1\n", "y = 2\n"]},
        {"cell_type": "raw", "source": ["raw content\n"]},
    ],
}


def test_returns_only_code_cells():
    sources = extract_cell_sources(json.dumps(NOTEBOOK))
    assert len(sources) == 2


def test_joins_source_lines():
    sources = extract_cell_sources(json.dumps(NOTEBOOK))
    assert sources[0] == "import os\nimport sys\n"
    assert sources[1] == "x = 1\ny = 2\n"


def test_skips_markdown_cells():
    sources = extract_cell_sources(json.dumps(NOTEBOOK))
    assert not any("Title" in s for s in sources)


def test_skips_raw_cells():
    sources = extract_cell_sources(json.dumps(NOTEBOOK))
    assert not any("raw content" in s for s in sources)


def test_empty_cells_list():
    raw = json.dumps({"nbformat": 4, "cells": []})
    assert extract_cell_sources(raw) == []


def test_missing_cells_key():
    raw = json.dumps({"nbformat": 4})
    assert extract_cell_sources(raw) == []


def test_source_as_plain_string():
    nb = {"nbformat": 4, "cells": [{"cell_type": "code", "source": "import x\n"}]}
    sources = extract_cell_sources(json.dumps(nb))
    assert sources == ["import x\n"]


def test_empty_source_cell_excluded():
    nb = {"nbformat": 4, "cells": [{"cell_type": "code", "source": []}]}
    assert extract_cell_sources(json.dumps(nb)) == []


def test_invalid_json_raises():
    with pytest.raises(json.JSONDecodeError):
        extract_cell_sources("{not valid json{{")
