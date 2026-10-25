"""Unit tests for PloneConnection (HTTP layer)."""

from __future__ import annotations

from plone_client.config import PloneClientConfig
from plone_client.connection import PloneConnection
from plone_client.exceptions import PloneAPIError
from plone_client.exceptions import PloneAuthenticationError
from plone_client.exceptions import PloneConflictError
from plone_client.exceptions import PloneForbiddenError
from plone_client.exceptions import PloneNotFoundError
from plone_client.exceptions import PloneServerError
from plone_client.exceptions import PloneTimeoutError

import pytest
import responses as resp_mock


BASE = "http://localhost:8080/Plone"


def _cfg(**kwargs: object) -> PloneClientConfig:
    defaults = {
        "base_url": BASE,
        "username": "admin",
        "password": "admin",
        "max_retries": 1,
        "retry_backoff": 0,
    }
    defaults.update(kwargs)
    return PloneClientConfig(**defaults)  # type: ignore[arg-type]


@pytest.mark.unit
class TestPloneConnectionLogin:
    @resp_mock.activate
    def test_login_stores_token(self) -> None:
        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/@login",
            json={"token": "jwt-token-abc"},
            status=200,
        )
        conn = PloneConnection(_cfg())
        conn.login()
        assert conn.token == "jwt-token-abc"
        assert conn._session.headers["Authorization"] == "Bearer jwt-token-abc"

    @resp_mock.activate
    def test_login_raises_on_401(self) -> None:
        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/@login",
            json={"message": "Wrong credentials"},
            status=401,
        )
        conn = PloneConnection(_cfg())
        with pytest.raises(PloneAuthenticationError):
            conn.login()

    def test_login_raises_without_credentials(self) -> None:
        from plone_client.exceptions import PloneClientError

        conn = PloneConnection(_cfg(username="", password=""))
        with pytest.raises(PloneClientError, match="no username/password"):
            conn.login()

    @resp_mock.activate
    def test_logout_clears_token(self) -> None:
        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/@login",
            json={"token": "tok"},
            status=200,
        )
        resp_mock.add(resp_mock.POST, f"{BASE}/@logout", json={}, status=200)
        conn = PloneConnection(_cfg())
        conn.login()
        assert conn.token == "tok"
        conn.logout()
        assert conn.token == ""
        assert "Authorization" not in conn._session.headers


@pytest.mark.unit
class TestPloneConnectionStatusMapping:
    @pytest.mark.parametrize(
        "status,exc",
        [
            (401, PloneAuthenticationError),
            (403, PloneForbiddenError),
            (404, PloneNotFoundError),
            (409, PloneConflictError),
            (500, PloneServerError),
            (503, PloneServerError),
        ],
    )
    @resp_mock.activate
    def test_status_raises_correct_exception(self, status: int, exc: type) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@search",
            json={"message": "error"},
            status=status,
        )
        conn = PloneConnection(_cfg(max_retries=0))
        with pytest.raises(exc):
            conn.get("/@search")

    @resp_mock.activate
    def test_422_raises_api_error(self) -> None:
        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/",
            json={"message": "Validation failed"},
            status=422,
        )
        conn = PloneConnection(_cfg(max_retries=0))
        with pytest.raises(PloneAPIError) as exc_info:
            conn.post("/")
        assert exc_info.value.status_code == 422


@pytest.mark.unit
class TestPloneConnectionRetry:
    @resp_mock.activate
    def test_retries_on_timeout_then_succeeds(self) -> None:
        import requests as _req

        resp_mock.add(resp_mock.GET, f"{BASE}/@search", body=_req.exceptions.Timeout())
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@search",
            json={"items": [], "items_total": 0},
            status=200,
        )
        conn = PloneConnection(_cfg(max_retries=1, retry_backoff=0))
        result = conn.get("/@search").json()
        assert result["items_total"] == 0

    @resp_mock.activate
    def test_raises_timeout_after_all_retries(self) -> None:
        import requests as _req

        resp_mock.add(resp_mock.GET, f"{BASE}/@search", body=_req.exceptions.Timeout())
        resp_mock.add(resp_mock.GET, f"{BASE}/@search", body=_req.exceptions.Timeout())
        conn = PloneConnection(_cfg(max_retries=1, retry_backoff=0))
        with pytest.raises(PloneTimeoutError):
            conn.get("/@search")

    @resp_mock.activate
    def test_retries_on_503(self) -> None:
        resp_mock.add(resp_mock.GET, f"{BASE}/@search", json={}, status=503)
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@search",
            json={"items": [], "items_total": 0},
            status=200,
        )
        conn = PloneConnection(_cfg(max_retries=1, retry_backoff=0))
        result = conn.get("/@search").json()
        assert result["items_total"] == 0

    @resp_mock.activate
    def test_no_retry_on_404(self) -> None:
        """404 should not be retried — only idempotent methods retry on 5xx/429."""
        resp_mock.add(resp_mock.GET, f"{BASE}/missing", json={}, status=404)
        conn = PloneConnection(_cfg(max_retries=3, retry_backoff=0))
        with pytest.raises(PloneNotFoundError):
            conn.get("/missing")
        # Only one call should have been made
        assert len(resp_mock.calls) == 1


@pytest.mark.unit
class TestPloneConnectionURLBuilding:
    def test_relative_path(self) -> None:
        conn = PloneConnection(_cfg())
        assert conn._build_url("/@search") == f"{BASE}/@search"

    def test_absolute_url_passthrough(self) -> None:
        conn = PloneConnection(_cfg())
        url = "https://other.site/path"
        assert conn._build_url(url) == url

    def test_double_slash_stripped(self) -> None:
        conn = PloneConnection(_cfg())
        assert conn._build_url("//@search") == f"{BASE}/@search"
