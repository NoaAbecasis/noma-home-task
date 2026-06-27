from unittest.mock import patch

import httpx
import pytest
import respx

from fetchers.http_fetcher import _is_retryable, fetch


# ---------------------------------------------------------------------------
# Basic behaviour
# ---------------------------------------------------------------------------

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
    with patch("fetchers.http_fetcher.httpx.Client") as mock_cls:
        instance = mock_cls.return_value.__enter__.return_value
        mock_req = httpx.Request("GET", "https://example.com")
        instance.get.return_value = httpx.Response(200, text="ok", request=mock_req)
        fetch("https://example.com")
    mock_cls.assert_called_once()
    assert mock_cls.call_args.kwargs.get("follow_redirects") is True


# ---------------------------------------------------------------------------
# _is_retryable predicate
# ---------------------------------------------------------------------------

def _status_error(status: int) -> httpx.HTTPStatusError:
    req = httpx.Request("GET", "https://example.com")
    return httpx.HTTPStatusError("err", request=req, response=httpx.Response(status, request=req))


def test_is_retryable_500():
    assert _is_retryable(_status_error(500)) is True


def test_is_retryable_502():
    assert _is_retryable(_status_error(502)) is True


def test_is_retryable_503():
    assert _is_retryable(_status_error(503)) is True


def test_is_retryable_404_false():
    assert _is_retryable(_status_error(404)) is False


def test_is_retryable_403_false():
    assert _is_retryable(_status_error(403)) is False


def test_is_retryable_connect_error():
    assert _is_retryable(httpx.ConnectError("refused")) is True


def test_is_retryable_timeout():
    assert _is_retryable(httpx.TimeoutException("timed out")) is True


def test_is_retryable_remote_protocol_error():
    req = httpx.Request("GET", "https://example.com")
    assert _is_retryable(httpx.RemoteProtocolError("bad frame", request=req)) is True


def test_is_retryable_value_error_false():
    assert _is_retryable(ValueError("unrelated")) is False


# ---------------------------------------------------------------------------
# Retry behaviour
# ---------------------------------------------------------------------------

@respx.mock
def test_retries_on_500_and_eventually_succeeds():
    route = respx.get("https://example.com").mock(side_effect=[
        httpx.Response(500),
        httpx.Response(500),
        httpx.Response(200, text="recovered"),
    ])
    with patch("time.sleep"):
        result = fetch("https://example.com")
    assert result == "recovered"
    assert route.call_count == 3


@respx.mock
def test_retries_on_connect_error_and_eventually_succeeds():
    route = respx.get("https://example.com").mock(side_effect=[
        httpx.ConnectError("refused"),
        httpx.Response(200, text="ok"),
    ])
    with patch("time.sleep"):
        result = fetch("https://example.com")
    assert result == "ok"
    assert route.call_count == 2


@respx.mock
def test_retries_on_timeout_and_eventually_succeeds():
    route = respx.get("https://example.com").mock(side_effect=[
        httpx.TimeoutException("timed out"),
        httpx.Response(200, text="ok"),
    ])
    with patch("time.sleep"):
        result = fetch("https://example.com")
    assert result == "ok"
    assert route.call_count == 2


@respx.mock
def test_exhausts_all_retries_and_reraises_500():
    route = respx.get("https://example.com").mock(return_value=httpx.Response(503))
    with patch("time.sleep"):
        with pytest.raises(httpx.HTTPStatusError) as exc_info:
            fetch("https://example.com")
    assert exc_info.value.response.status_code == 503
    assert route.call_count == 3  # 1 initial + 2 retries


@respx.mock
def test_exhausts_all_retries_and_reraises_connect_error():
    route = respx.get("https://example.com").mock(
        side_effect=httpx.ConnectError("refused")
    )
    with patch("time.sleep"):
        with pytest.raises(httpx.ConnectError):
            fetch("https://example.com")
    assert route.call_count == 3


@respx.mock
def test_no_retry_on_404():
    route = respx.get("https://example.com").mock(return_value=httpx.Response(404))
    with patch("time.sleep"):
        with pytest.raises(httpx.HTTPStatusError):
            fetch("https://example.com")
    assert route.call_count == 1  # no retry for client errors


@respx.mock
def test_no_retry_on_403():
    route = respx.get("https://example.com").mock(return_value=httpx.Response(403))
    with patch("time.sleep"):
        with pytest.raises(httpx.HTTPStatusError):
            fetch("https://example.com")
    assert route.call_count == 1


@respx.mock
def test_success_on_first_attempt_makes_one_call():
    route = respx.get("https://example.com").mock(return_value=httpx.Response(200, text="ok"))
    result = fetch("https://example.com")
    assert result == "ok"
    assert route.call_count == 1
