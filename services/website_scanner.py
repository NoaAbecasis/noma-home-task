from api.models import ScanRequest, ScanResponse
from fetchers import http_fetcher
from services import regex_engine


def scan(request: ScanRequest) -> ScanResponse:
    options = request.options or {}
    content = http_fetcher.fetch(
        url=request.location,
        headers=options.get("headers"),
        timeout=float(options.get("timeout", 30.0)),
    )
    results = regex_engine.apply_patterns(content, request.patterns)
    return ScanResponse(
        source_type=request.source_type,
        location=request.location,
        results=results,
    )
