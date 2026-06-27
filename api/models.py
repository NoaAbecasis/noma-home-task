from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ScanRequest(BaseModel):
    source_type: Literal["url", "file", "code", "notebook"] = Field(
        ...,
        description=(
            "The type of source to scan. "
            "`url` fetches an HTML page via HTTP. "
            "`file` reads a local file by path. "
            "`code` scans source code — auto-detects HTTP vs local from the `location` value. "
            "`notebook` fetches a Jupyter `.ipynb` file (HTTP or local), parses it, and scans code-cell sources."
        ),
        examples=["url", "file", "code", "notebook"],
    )
    location: str = Field(
        ...,
        description=(
            "The resource to scan. "
            "For `url` and `code` (HTTP): a full URL (e.g. `https://example.com`). "
            "For `file` and `code` (local): an absolute or relative filesystem path."
        ),
        examples=["https://example.com", "/home/user/app.py"],
    )
    patterns: list[str] = Field(
        ...,
        min_length=1,
        description=(
            "One or more Python-compatible regex patterns to search for in the content. "
            "All patterns are compiled with `re.MULTILINE`, so `^` and `$` match per line. "
            "Full matches (group 0) are returned — capture groups do not affect what is returned."
        ),
        examples=[
            [r'href="(https?://[^"]+)"'],
            [r"^import\s+\S+", r"^from\s+\S+\s+import\s+\S+"],
        ],
    )
    options: Optional[dict[str, Any]] = Field(
        default=None,
        description=(
            "Optional settings depending on source type. "
            "Supported keys: "
            "`headers` (dict) — HTTP headers attached to the request (e.g. `Authorization`); "
            "`timeout` (float) — HTTP request timeout in seconds (default 30); "
            "`encoding` (str) — file character encoding (default `utf-8`)."
        ),
        examples=[
            {"headers": {"Authorization": "Bearer <token>"}, "timeout": 15},
            {"encoding": "latin-1"},
        ],
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "summary": "Scan a website for outbound links",
                    "value": {
                        "source_type": "url",
                        "location": "https://example.com",
                        "patterns": [r'href="(https?://[^"]+)"'],
                        "options": {"headers": {"User-Agent": "link-scanner/1.0"}},
                    },
                },
                {
                    "summary": "Scan a remote Python file for import statements",
                    "value": {
                        "source_type": "code",
                        "location": "https://raw.githubusercontent.com/org/repo/main/app.py",
                        "patterns": [r"^import\s+\S+", r"^from\s+\S+\s+import\s+\S+"],
                        "options": {"headers": {"Authorization": "Bearer <token>"}},
                    },
                },
                {
                    "summary": "Scan a local Go file for import statements",
                    "value": {
                        "source_type": "code",
                        "location": "/home/user/project/main.go",
                        "patterns": [r'import\s+"[^"]+"'],
                    },
                },
                {
                    "summary": "Scan a Jupyter notebook for suspicious imports",
                    "value": {
                        "source_type": "notebook",
                        "location": "https://raw.githubusercontent.com/org/repo/main/analysis.ipynb",
                        "patterns": [r"^import\s+\S+", r"^from\s+\S+\s+import\s+\S+"],
                        "options": {"headers": {"Authorization": "Bearer <token>"}},
                    },
                },
            ]
        }
    }


class PatternMatch(BaseModel):
    pattern: str = Field(..., description="The regex pattern that was applied.")
    matches: list[str] = Field(
        ...,
        description="All full matches found in the content for this pattern.",
    )


class ScanResponse(BaseModel):
    source_type: str = Field(..., description="The source type from the request.")
    location: str = Field(..., description="The location that was scanned.")
    results: list[PatternMatch] = Field(
        ...,
        description="One entry per pattern, in the same order as the request.",
    )
