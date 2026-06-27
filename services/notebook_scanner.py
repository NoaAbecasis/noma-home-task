from api.models import ScanRequest, ScanResponse
from fetchers import content_fetcher
from parsers import notebook_parser
from services import regex_engine


def scan(request: ScanRequest) -> ScanResponse:
    raw = content_fetcher.fetch(request.location, request.options or {})
    cell_sources = notebook_parser.extract_cell_sources(raw)
    combined = "\n".join(cell_sources)
    results = regex_engine.apply_patterns(combined, request.patterns)
    return ScanResponse(
        source_type=request.source_type,
        location=request.location,
        results=results,
    )
