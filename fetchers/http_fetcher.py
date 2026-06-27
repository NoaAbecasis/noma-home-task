from typing import Optional

import httpx


def fetch(url: str, headers: Optional[dict[str, str]] = None, timeout: float = 30.0) -> str:
    with httpx.Client(follow_redirects=True, timeout=timeout) as client:
        response = client.get(url, headers=headers or {})
        response.raise_for_status()
        return response.text
