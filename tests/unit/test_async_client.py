"""
Unit tests for AsyncPloneClient.

We use ``respx`` to mock ``httpx`` calls without real network access.
These tests are marked ``asyncio`` and require ``pytest-asyncio``.
"""

from __future__ import annotations

import pytest


# Guard: skip entire module if httpx/respx not available
pytest.importorskip("httpx")
pytest.importorskip("respx")

from plone_client.async_client import _raise_for_status
from plone_client.async_client import AsyncPloneClient
from plone_client.config import PloneClientConfig
from plone_client.exceptions import PloneAuthenticationError
from plone_client.exceptions import PloneNotFoundError
from plone_client.exceptions import PloneServerError

import httpx
import respx


BASE = "http://localhost:8080/Plone"

pytestmark = pytest.mark.asyncio


def _cfg(**kwargs: object) -> PloneClientConfig:
    return PloneClientConfig(
        base_url=BASE,
        max_retries=1,
        retry_backoff=0,
        **kwargs,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# Status mapping (sync helper, no network needed)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRaiseForStatus:
    def test_2xx_returns_response(self) -> None:
        r = httpx.Response(200, json={"ok": True})
        assert _raise_for_status(r) is r

    def test_401_raises_auth_error(self) -> None:
        r = httpx.Response(401, json={"message": "Unauthorized"})
        with pytest.raises(PloneAuthenticationError):
            _raise_for_status(r)

    def test_404_raises_not_found(self) -> None:
        r = httpx.Response(404, json={"message": "Not found"})
        with pytest.raises(PloneNotFoundError):
            _raise_for_status(r)

    def test_500_raises_server_error(self) -> None:
        r = httpx.Response(500, text="Internal Server Error")
        with pytest.raises(PloneServerError):
            _raise_for_status(r)


# ---------------------------------------------------------------------------
# AsyncPloneClient — login / context manager
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAsyncPloneClientLogin:
    @respx.mock
    async def test_login_stores_token(self) -> None:
        respx.post(f"{BASE}/@login").mock(
            return_value=httpx.Response(200, json={"token": "async-tok"})
        )
        respx.post(f"{BASE}/@logout").mock(return_value=httpx.Response(200, json={}))

        async with AsyncPloneClient(
            BASE, username="admin", password="secret", max_retries=0
        ) as client:
            assert client.token == "async-tok"

    @respx.mock
    async def test_static_token_skips_login(self) -> None:
        client = AsyncPloneClient(BASE, token="static", max_retries=0)
        await client.open()
        assert client.token == "static"
        assert not respx.calls  # no HTTP calls made
        await client.close()


# ---------------------------------------------------------------------------
# AsyncPloneClient — managers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAsyncContentManager:
    @respx.mock
    async def test_get(self) -> None:
        respx.get(f"{BASE}/front-page").mock(
            return_value=httpx.Response(200, json={"title": "Front Page"})
        )
        client = AsyncPloneClient(BASE, token="tok", max_retries=0)
        result = await client.content.get("/front-page")
        assert result["title"] == "Front Page"

    @respx.mock
    async def test_create(self) -> None:
        respx.post(f"{BASE}/").mock(
            return_value=httpx.Response(201, json={"@type": "Document"})
        )
        client = AsyncPloneClient(BASE, token="tok", max_retries=0)
        result = await client.content.create("/", "Document", title="Test")
        assert result["@type"] == "Document"

    @respx.mock
    async def test_delete(self) -> None:
        respx.delete(f"{BASE}/old-page").mock(return_value=httpx.Response(204))
        client = AsyncPloneClient(BASE, token="tok", max_retries=0)
        await client.content.delete("/old-page")

    @respx.mock
    async def test_workflow_transition(self) -> None:
        respx.post(f"{BASE}/my-doc/@workflow/publish").mock(
            return_value=httpx.Response(200, json={"review_state": "published"})
        )
        client = AsyncPloneClient(BASE, token="tok", max_retries=0)
        result = await client.content.transition("/my-doc", "publish")
        assert result["review_state"] == "published"


@pytest.mark.unit
class TestAsyncSearchManager:
    @respx.mock
    async def test_search(self) -> None:
        respx.get(f"{BASE}/@search").mock(
            return_value=httpx.Response(200, json={"items": [], "items_total": 0})
        )
        client = AsyncPloneClient(BASE, token="tok", max_retries=0)
        result = await client.search.search({"portal_type": "Document"})
        assert result["items_total"] == 0

    @respx.mock
    async def test_async_iterate(self) -> None:
        respx.get(f"{BASE}/@search").mock(
            return_value=httpx.Response(
                200,
                json={
                    "items": [{"@id": f"{BASE}/a"}, {"@id": f"{BASE}/b"}],
                    "items_total": 2,
                },
            )
        )
        client = AsyncPloneClient(BASE, token="tok", max_retries=0)
        items = [item async for item in client.search.iterate(b_size=50)]
        assert len(items) == 2


@pytest.mark.unit
class TestAsyncEscapeHatch:
    @respx.mock
    async def test_raw_request(self) -> None:
        respx.get(f"{BASE}/@my-endpoint").mock(
            return_value=httpx.Response(200, json={"result": "ok"})
        )
        client = AsyncPloneClient(BASE, token="tok", max_retries=0)
        response = await client.request("GET", "/@my-endpoint")
        assert response.json() == {"result": "ok"}
