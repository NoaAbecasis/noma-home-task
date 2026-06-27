from typing import Any

from fetchers import file_fetcher, http_fetcher


def fetch(location: str, options: dict[str, Any]) -> str:
    if location.startswith(("http://", "https://")):
        return http_fetcher.fetch(
            url=location,
            headers=options.get("headers"),
            timeout=float(options.get("timeout", 30.0)),
        )
    return file_fetcher.fetch(
        path=location,
        encoding=options.get("encoding", "utf-8"),
    )
