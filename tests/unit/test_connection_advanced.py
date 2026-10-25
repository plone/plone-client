"""Unit tests for upgraded connection.py features and pagination helpers."""

from __future__ import annotations

from plone_client.config import PloneClientConfig
from plone_client.connection import _parse_retry_after
from plone_client.connection import PloneConnection
from plone_client.exceptions import PloneAuthenticationError
from plone_client.pagination import BatchResult
from plone_client.pagination import paginate
from unittest.mock import MagicMock

import pytest
import responses as resp_mock


BASE = "http://localhost:8080/Plone"


def _cfg(**kwargs: object) -> PloneClientConfig:
    defaults = {"base_url": BASE, "token": "tok", "max_retries": 1, "retry_backoff": 0}
    defaults.update(kwargs)
    return PloneClientConfig(**defaults)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Middleware hooks
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRequestHooks:
    @resp_mock.activate
    def test_request_hook_called(self) -> None:
        resp_mock.add(resp_mock.GET, f"{BASE}/@search", json={"items": []}, status=200)
        conn = PloneConnection(_cfg())
        calls: list[tuple[str, str]] = []

        def hook(method: str, url: str, kwargs: dict) -> None:
            calls.append((method, url))

        conn.add_request_hook(hook)
        conn.get("/@search")
        assert len(calls) == 1
        assert calls[0] == ("GET", f"{BASE}/@search")

    @resp_mock.activate
    def test_response_hook_called_with_elapsed(self) -> None:
        resp_mock.add(resp_mock.GET, f"{BASE}/@search", json={"items": []}, status=200)
        conn = PloneConnection(_cfg())
        recorded: list[tuple[int, float]] = []

        def hook(method: str, url: str, response: object, elapsed_ms: float) -> None:
            recorded.append((getattr(response, "status_code", 0), elapsed_ms))

        conn.add_response_hook(hook)
        conn.get("/@search")
        assert len(recorded) == 1
        status, elapsed = recorded[0]
        assert status == 200
        assert elapsed >= 0

    @resp_mock.activate
    def test_multiple_hooks_all_called(self) -> None:
        resp_mock.add(resp_mock.GET, f"{BASE}/@search", json={}, status=200)
        conn = PloneConnection(_cfg())
        log: list[str] = []
        conn.add_request_hook(lambda m, u, k: log.append("req1"))
        conn.add_request_hook(lambda m, u, k: log.append("req2"))
        conn.add_response_hook(lambda m, u, r, e: log.append("resp1"))
        conn.get("/@search")
        assert log == ["req1", "req2", "resp1"]

    @resp_mock.activate
    def test_broken_hook_does_not_crash_request(self) -> None:
        resp_mock.add(resp_mock.GET, f"{BASE}/@search", json={"items": []}, status=200)
        conn = PloneConnection(_cfg())

        def bad_hook(m: str, u: str, k: dict) -> None:
            raise RuntimeError("hook error")

        conn.add_request_hook(bad_hook)
        # Should not raise — hooks swallow their exceptions
        result = conn.get("/@search")
        assert result.status_code == 200


# ---------------------------------------------------------------------------
# Retry-After header parsing
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRetryAfter:
    def _resp(self, header_value: str) -> object:
        r = MagicMock()
        r.headers = {"Retry-After": header_value} if header_value else {}
        return r  # type: ignore[return-value]

    def test_numeric_seconds(self) -> None:
        r = MagicMock()
        r.headers = {"Retry-After": "30"}
        assert _parse_retry_after(r) == 30.0  # type: ignore[arg-type]

    def test_float_seconds(self) -> None:
        r = MagicMock()
        r.headers = {"Retry-After": "1.5"}
        assert _parse_retry_after(r) == 1.5  # type: ignore[arg-type]

    def test_missing_header_returns_zero(self) -> None:
        r = MagicMock()
        r.headers = {}
        assert _parse_retry_after(r) == 0.0  # type: ignore[arg-type]

    def test_negative_clamped_to_zero(self) -> None:
        r = MagicMock()
        r.headers = {"Retry-After": "-10"}
        assert _parse_retry_after(r) == 0.0  # type: ignore[arg-type]

    def test_invalid_string_returns_zero(self) -> None:
        r = MagicMock()
        r.headers = {"Retry-After": "not-a-date"}
        assert _parse_retry_after(r) == 0.0  # type: ignore[arg-type]

    @resp_mock.activate
    def test_429_retry_after_respected(self) -> None:
        """429 with Retry-After: 0 should still retry."""
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@search",
            json={},
            status=429,
            headers={"Retry-After": "0"},
        )
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@search",
            json={"items": [], "items_total": 0},
            status=200,
        )
        conn = PloneConnection(_cfg(max_retries=1, retry_backoff=0))
        result = conn.get("/@search")
        assert result.status_code == 200
        assert len(resp_mock.calls) == 2


# ---------------------------------------------------------------------------
# Correlation ID (X-Request-ID: auto)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCorrelationId:
    @resp_mock.activate
    def test_auto_generates_uuid_per_request(self) -> None:
        resp_mock.add(resp_mock.GET, f"{BASE}/@search", json={}, status=200)
        resp_mock.add(resp_mock.GET, f"{BASE}/@search", json={}, status=200)

        cfg = PloneClientConfig(
            base_url=BASE,
            token="tok",
            max_retries=0,
            extra_headers={"X-Request-ID": "auto"},
        )
        conn = PloneConnection(cfg)
        conn.get("/@search")
        conn.get("/@search")

        ids = [call.request.headers.get("X-Request-ID") for call in resp_mock.calls]
        assert all(ids), "X-Request-ID header missing"
        # Each request should have a unique ID
        assert ids[0] != ids[1], "Expected unique IDs per request"

    @resp_mock.activate
    def test_static_extra_header_forwarded(self) -> None:
        resp_mock.add(resp_mock.GET, f"{BASE}/@search", json={}, status=200)
        cfg = PloneClientConfig(
            base_url=BASE,
            token="tok",
            max_retries=0,
            extra_headers={"X-App-Name": "myapp"},
        )
        conn = PloneConnection(cfg)
        conn.get("/@search")
        assert resp_mock.calls[0].request.headers.get("X-App-Name") == "myapp"


# ---------------------------------------------------------------------------
# Auto token renewal on 401
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAutoRenew:
    @resp_mock.activate
    def test_401_triggers_renew_then_retry(self) -> None:
        # First request returns 401
        resp_mock.add(resp_mock.GET, f"{BASE}/@search", json={}, status=401)
        # Token renewal succeeds
        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/@login-renew",
            json={"token": "new-tok"},
            status=200,
        )
        # Retry succeeds
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@search",
            json={"items": [], "items_total": 0},
            status=200,
        )
        conn = PloneConnection(
            PloneClientConfig(
                base_url=BASE,
                username="admin",
                password="pass",
                token="old-tok",
                max_retries=1,
                retry_backoff=0,
            )
        )
        result = conn.get("/@search")
        assert result.status_code == 200
        assert conn.token == "new-tok"

    @resp_mock.activate
    def test_401_raises_if_no_credentials(self) -> None:
        resp_mock.add(resp_mock.GET, f"{BASE}/@search", json={}, status=401)
        conn = PloneConnection(_cfg(max_retries=0))
        with pytest.raises(PloneAuthenticationError):
            conn.get("/@search")


# ---------------------------------------------------------------------------
# Proxy config
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestProxyConfig:
    def test_proxies_set_on_session(self) -> None:
        cfg = PloneClientConfig(
            base_url=BASE,
            token="tok",
            proxies={"https": "http://proxy.corp:8080"},
        )
        conn = PloneConnection(cfg)
        assert conn._session.proxies.get("https") == "http://proxy.corp:8080"


# ---------------------------------------------------------------------------
# BatchResult
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestBatchResult:
    def _raw(self, items: list, total: int, next_url: str | None = None) -> dict:
        raw: dict = {"items": items, "items_total": total}
        if next_url:
            raw["batching"] = {"next": next_url}
        return raw

    def test_items_and_total(self) -> None:
        br = BatchResult(self._raw([{"@id": "/a"}], 1))
        assert len(br) == 1
        assert br.items_total == 1

    def test_has_next(self) -> None:
        br = BatchResult(self._raw([], 100, next_url="http://x/@search?b_start=25"))
        assert br.has_next is True

    def test_no_next(self) -> None:
        br = BatchResult(self._raw([], 5))
        assert br.has_next is False

    def test_iter(self) -> None:
        items = [{"@id": "/a"}, {"@id": "/b"}]
        br = BatchResult(self._raw(items, 2))
        assert list(br) == items

    def test_total_pages(self) -> None:
        # 100 items, 25 per page → 4 pages
        br = BatchResult({"items": [{}] * 25, "items_total": 100})
        assert br.total_pages == 4

    def test_repr(self) -> None:
        br = BatchResult(self._raw([{}], 1))
        assert "BatchResult" in repr(br)


# ---------------------------------------------------------------------------
# paginate() helper
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPaginate:
    def _make_fetch(self, all_items: list) -> object:
        def fetch(b_size: int = 25, b_start: int = 0, **kw: object) -> dict:
            page = all_items[b_start : b_start + b_size]
            return {"items": page, "items_total": len(all_items)}

        return fetch  # type: ignore[return-value]

    def test_single_page(self) -> None:
        fetch = self._make_fetch([{"i": i} for i in range(5)])
        result = list(paginate(fetch, b_size=10))  # type: ignore[arg-type]
        assert len(result) == 5

    def test_multiple_pages(self) -> None:
        fetch = self._make_fetch([{"i": i} for i in range(55)])
        result = list(paginate(fetch, b_size=25))  # type: ignore[arg-type]
        assert len(result) == 55

    def test_max_items_limit(self) -> None:
        fetch = self._make_fetch([{"i": i} for i in range(100)])
        result = list(paginate(fetch, b_size=25, max_items=10))  # type: ignore[arg-type]
        assert len(result) == 10

    def test_empty_result(self) -> None:
        fetch = self._make_fetch([])
        result = list(paginate(fetch))  # type: ignore[arg-type]
        assert result == []

    def test_kwargs_forwarded(self) -> None:
        received: list[dict] = []

        def fetch(b_size: int = 25, b_start: int = 0, **kw: object) -> dict:
            received.append(dict(kw))
            return {"items": [], "items_total": 0}

        list(paginate(fetch, portal_type="Document"))  # type: ignore[arg-type]
        assert received[0].get("portal_type") == "Document"
