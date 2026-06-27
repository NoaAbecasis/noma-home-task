from typing import Callable

from api.models import ScanRequest, ScanResponse
from fetchers import file_fetcher
from services import code_scanner, notebook_scanner, regex_engine, website_scanner


def _scan_file(request: ScanRequest) -> ScanResponse:
    options = request.options or {}
    content = file_fetcher.fetch(
        path=request.location,
        encoding=options.get("encoding", "utf-8"),
    )
    results = regex_engine.apply_patterns(content, request.patterns)
    return ScanResponse(
        source_type=request.source_type,
        location=request.location,
        results=results,
    )


_SCANNERS: dict[str, Callable[[ScanRequest], ScanResponse]] = {
    "url": website_scanner.scan,
    "file": _scan_file,
    "code": code_scanner.scan,
    "notebook": notebook_scanner.scan,
}


def scan(request: ScanRequest) -> ScanResponse:
    scanner = _SCANNERS.get(request.source_type)
    if scanner is None:
        raise ValueError(f"Unsupported source type: {request.source_type!r}")
    return scanner(request)
