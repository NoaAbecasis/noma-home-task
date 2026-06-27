import json
import re

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from api.models import ScanRequest, ScanResponse
from services.source_scanner import scan

router = APIRouter(tags=["Scanning"])


@router.post(
    "/scan",
    response_model=ScanResponse,
    summary="Scan a source for regex pattern matches",
    description=(
        "Fetches content from the specified source, applies each regex pattern, "
        "and returns all matches grouped by pattern.\n\n"
        "**Source types**\n"
        "| `source_type` | Fetch mechanism | Typical use |\n"
        "|---|---|---|\n"
        "| `url` | HTTP GET | Scan an HTML page for outbound links |\n"
        "| `file` | Local filesystem | Scan a local text file |\n"
        "| `code` | Auto-detected from `location` | Scan source code from GitHub or disk |\n\n"
        "**Authentication / custom headers**\n\n"
        "Pass an `options.headers` dict to attach arbitrary HTTP headers to the request, "
        "for example `{\"Authorization\": \"Bearer <token>\"}` for private repositories.\n\n"
        "**Regex flags**\n\n"
        "All patterns are compiled with `re.MULTILINE`, so `^` and `$` anchor to the "
        "start and end of each line rather than the whole string."
    ),
    responses={
        200: {
            "description": "Scan completed — results contain matches per pattern (may be empty lists).",
            "content": {
                "application/json": {
                    "examples": {
                        "link_scan": {
                            "summary": "Website link scan",
                            "value": {
                                "source_type": "url",
                                "location": "https://example.com",
                                "results": [
                                    {
                                        "pattern": r'href="(https?://[^"]+)"',
                                        "matches": [
                                            'href="https://www.iana.org/domains/example"',
                                        ],
                                    }
                                ],
                            },
                        },
                        "code_scan": {
                            "summary": "Python import scan",
                            "value": {
                                "source_type": "code",
                                "location": "https://raw.githubusercontent.com/org/repo/main/app.py",
                                "results": [
                                    {
                                        "pattern": r"^import\s+\S+",
                                        "matches": ["import os", "import sys"],
                                    },
                                    {
                                        "pattern": r"^from\s+\S+\s+import\s+\S+",
                                        "matches": ["from pathlib import Path"],
                                    },
                                ],
                            },
                        },
                    }
                }
            },
        },
        400: {"description": "Bad request — unsupported `source_type` or file not found."},
        422: {"description": "Validation error — invalid request body or malformed regex pattern."},
        502: {"description": "Bad gateway — the upstream HTTP source returned an error or was unreachable."},
    },
)
def scan_endpoint(request: ScanRequest) -> ScanResponse:
    try:
        return scan(request)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Invalid notebook JSON: {e}")
    except re.error as e:
        raise HTTPException(status_code=422, detail=f"Invalid regex pattern: {e}")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"Upstream request failed: {e.response.status_code}")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Failed to reach {request.location}: {e}")
    except FileNotFoundError:
        raise HTTPException(status_code=400, detail=f"File not found: {request.location}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
