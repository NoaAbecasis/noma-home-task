from unittest.mock import patch

import httpx
import pytest
import respx

from fetchers.http_fetcher import fetch


@respx.mock
def test_returns_response_text():
    respx.get("https://example.com").mock(return_value=httpx.Response(200, text="<html>content</html>"))
    assert fetch("https://example.com") == "<html>content</html>"


@respx.mock
def test_passes_custom_headers():
    route = respx.get("https://example.com").mock(return_value=httpx.Response(200, text="ok"))
    fetch("https://example.com", headers={"X-Token": "abc"})
    assert route.called
    assert route.calls.last.request.headers["x-token"] == "abc"


@respx.mock
def test_http_error_raises():
    respx.get("https://example.com").mock(return_value=httpx.Response(404))
    with pytest.raises(httpx.HTTPStatusError):
        fetch("https://example.com")


def test_follow_redirects_is_enabled():
    # Verify follow_redirects=True is passed to the httpx.Client constructor
    with patch("fetchers.http_fetcher.httpx.Client") as mock_cls:
        instance = mock_cls.return_value.__enter__.return_value
        mock_req = httpx.Request("GET", "https://example.com")
        instance.get.return_value = httpx.Response(200, text="ok", request=mock_req)
        fetch("https://example.com")
    mock_cls.assert_called_once()
    assert mock_cls.call_args.kwargs.get("follow_redirects") is True
