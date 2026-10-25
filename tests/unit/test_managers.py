"""Unit tests for resource managers."""

from __future__ import annotations

from plone_client import PloneClient
from plone_client.config import PloneClientConfig

import pytest
import responses as resp_mock


BASE = "http://localhost:8080/Plone"


@pytest.fixture()
def cli() -> PloneClient:
    cfg = PloneClientConfig(
        base_url=BASE,
        token="test-token",
        max_retries=0,
        retry_backoff=0,
    )
    return PloneClient(config=cfg)


# ---------------------------------------------------------------------------
# ContentManager
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestContentManager:
    @resp_mock.activate
    def test_get(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/front-page",
            json={"@type": "Document", "title": "Front Page"},
        )
        result = cli.content.get("/front-page")
        assert result["title"] == "Front Page"

    @resp_mock.activate
    def test_create(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/",
            json={"@id": f"{BASE}/my-page", "@type": "Document"},
            status=201,
        )
        result = cli.content.create("/", "Document", title="My Page")
        assert result["@type"] == "Document"

    @resp_mock.activate
    def test_update(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.PATCH,
            f"{BASE}/my-page",
            json={"title": "Updated Title"},
        )
        result = cli.content.update("/my-page", title="Updated Title")
        assert result["title"] == "Updated Title"

    @resp_mock.activate
    def test_delete(self, cli: PloneClient) -> None:
        resp_mock.add(resp_mock.DELETE, f"{BASE}/my-page", status=204)
        # Should not raise
        cli.content.delete("/my-page")

    @resp_mock.activate
    def test_workflow_transition(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/my-page/@workflow/publish",
            json={"review_state": "published"},
        )
        result = cli.content.transition("/my-page", "publish", comment="LGTM")
        assert result["review_state"] == "published"

    @resp_mock.activate
    def test_copy(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/my-page/@copy",
            json={"target": "/news"},
        )
        cli.content.copy("/my-page", "/news")
        assert resp_mock.calls[0].request.body  # type: ignore[union-attr]

    @resp_mock.activate
    def test_navigation(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@navigation",
            json={"@id": f"{BASE}/@navigation", "items": []},
        )
        result = cli.content.navigation()
        assert "items" in result


# ---------------------------------------------------------------------------
# SearchManager
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSearchManager:
    @resp_mock.activate
    def test_search_basic(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@search",
            json={"items": [{"@id": f"{BASE}/doc"}], "items_total": 1},
        )
        result = cli.search.search({"portal_type": "Document"})
        assert result["items_total"] == 1

    @resp_mock.activate
    def test_search_fullobjects(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@search",
            json={"items": [], "items_total": 0},
        )
        cli.search.search(fullobjects=True)
        assert "fullobjects=1" in resp_mock.calls[0].request.url

    @resp_mock.activate
    def test_iterate_single_page(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@search",
            json={
                "items": [{"@id": f"{BASE}/a"}, {"@id": f"{BASE}/b"}],
                "items_total": 2,
            },
        )
        items = list(cli.search.iterate(b_size=50))
        assert len(items) == 2

    @resp_mock.activate
    def test_iterate_multiple_pages(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@search",
            json={"items": [{"@id": f"{BASE}/a"}], "items_total": 2},
        )
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@search",
            json={"items": [{"@id": f"{BASE}/b"}], "items_total": 2},
        )
        items = list(cli.search.iterate(b_size=1))
        assert len(items) == 2

    @resp_mock.activate
    def test_querystring(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/@querystring-search",
            json={"items": [], "items_total": 0},
        )
        result = cli.search.querystring([
            {
                "i": "portal_type",
                "o": "plone.app.querystring.operation.selection.any",
                "v": ["Document"],
            }
        ])
        assert result["items_total"] == 0


# ---------------------------------------------------------------------------
# UsersManager
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestUsersManager:
    @resp_mock.activate
    def test_list_users(self, cli: PloneClient) -> None:
        resp_mock.add(resp_mock.GET, f"{BASE}/@users", json=[{"id": "admin"}])
        result = cli.users.list()
        assert result[0]["id"] == "admin"

    @resp_mock.activate
    def test_create_user(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/@users",
            json={"id": "newuser"},
            status=201,
        )
        result = cli.users.create("newuser", "newuser@example.com", password="secret")
        assert result["id"] == "newuser"

    @resp_mock.activate
    def test_delete_user(self, cli: PloneClient) -> None:
        resp_mock.add(resp_mock.DELETE, f"{BASE}/@users/olduser", status=204)
        cli.users.delete("olduser")


# ---------------------------------------------------------------------------
# SiteManager
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSiteManager:
    @resp_mock.activate
    def test_info(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/",
            json={"@type": "Plone Site", "id": "Plone"},
        )
        result = cli.site.info()
        assert result["@type"] == "Plone Site"

    @resp_mock.activate
    def test_types(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@types",
            json=[{"@id": f"{BASE}/@types/Document", "title": "Page"}],
        )
        result = cli.site.types()
        assert result[0]["title"] == "Page"

    @resp_mock.activate
    def test_vocabulary(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@vocabularies/plone.app.vocabularies.Keywords",
            json={"items": [], "items_total": 0},
        )
        result = cli.site.vocabulary("plone.app.vocabularies.Keywords")
        assert "items" in result


# ---------------------------------------------------------------------------
# CommentsManager
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCommentsManager:
    @resp_mock.activate
    def test_add_comment(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/my-doc/@comments",
            json={"comment_id": "123", "text": "Nice post!"},
            status=201,
        )
        result = cli.comments.add("/my-doc", "Nice post!")
        assert result["comment_id"] == "123"

    @resp_mock.activate
    def test_delete_comment(self, cli: PloneClient) -> None:
        resp_mock.add(resp_mock.DELETE, f"{BASE}/my-doc/@comments/123", status=204)
        cli.comments.delete("/my-doc", "123")


# ---------------------------------------------------------------------------
# RegistryManager
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRegistryManager:
    @resp_mock.activate
    def test_get_all(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@registry",
            json={"items": {}, "items_total": 0},
        )
        result = cli.registry.get()
        assert "items" in result

    @resp_mock.activate
    def test_set_key(self, cli: PloneClient) -> None:
        key = "plone.site_title"
        resp_mock.add(resp_mock.PATCH, f"{BASE}/@registry/{key}", status=204)
        cli.registry.set(key, "My Plone Site")
