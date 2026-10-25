"""Unit tests for the PloneClient facade."""

from __future__ import annotations

from plone_client import PloneClient
from plone_client.config import PloneClientConfig

import pytest
import responses as resp_mock


BASE = "http://localhost:8080/Plone"


def _client(**kwargs: object) -> PloneClient:
    cfg = PloneClientConfig(
        base_url=BASE,
        username="admin",
        password="admin",
        max_retries=0,
        retry_backoff=0,
        **kwargs,  # type: ignore[arg-type]
    )
    return PloneClient(config=cfg)


@pytest.mark.unit
class TestPloneClientInit:
    def test_keyword_args_forwarded(self) -> None:
        c = PloneClient(BASE, username="u", password="p")
        assert c.config.base_url == BASE
        assert c.config.username == "u"

    def test_config_object_accepted(self) -> None:
        cfg = PloneClientConfig(base_url=BASE)
        c = PloneClient(config=cfg)
        assert c.config is cfg

    def test_managers_initialised(self) -> None:
        c = _client()
        for attr in (
            "content",
            "search",
            "users",
            "groups",
            "sharing",
            "registry",
            "controlpanels",
            "addons",
            "site",
            "comments",
            "history",
            "tiles",
        ):
            assert hasattr(c, attr), f"missing manager: {attr}"


@pytest.mark.unit
class TestPloneClientContextManager:
    @resp_mock.activate
    def test_open_triggers_login(self) -> None:
        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/@login",
            json={"token": "tok"},
            status=200,
        )
        resp_mock.add(resp_mock.POST, f"{BASE}/@logout", json={}, status=200)
        with _client() as c:
            assert c.token == "tok"

    @resp_mock.activate
    def test_static_token_skips_login(self) -> None:
        c = _client(token="static-tok", username="", password="")
        c.open()  # Should NOT call /@login
        assert c.token == "static-tok"
        assert len(resp_mock.calls) == 0
        c.close()


@pytest.mark.unit
class TestPloneClientEscapeHatch:
    @resp_mock.activate
    def test_raw_request(self) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@my-custom-endpoint",
            json={"result": 42},
            status=200,
        )
        c = _client(token="tok")
        response = c.request("GET", "/@my-custom-endpoint")
        assert response.json() == {"result": 42}

    @resp_mock.activate
    def test_shorthand_get(self) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@search",
            json={"items": []},
            status=200,
        )
        c = _client(token="tok")
        r = c.get("/@search")
        assert r.status_code == 200

    @resp_mock.activate
    def test_shorthand_post(self) -> None:
        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/news",
            json={"@id": f"{BASE}/news/my-doc"},
            status=201,
        )
        c = _client(token="tok")
        r = c.post("/news", json={"@type": "Document", "title": "My Doc"})
        assert r.status_code == 201
