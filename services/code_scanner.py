from api.models import ScanRequest, ScanResponse
from fetchers import content_fetcher
from services import regex_engine


def scan(request: ScanRequest) -> ScanResponse:
    content = content_fetcher.fetch(request.location, request.options or {})
    results = regex_engine.apply_patterns(content, request.patterns)
    return ScanResponse(
        source_type=request.source_type,
        location=request.location,
        results=results,
    )
