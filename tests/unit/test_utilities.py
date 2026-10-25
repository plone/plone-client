"""Unit tests for UtilitiesManager."""

from __future__ import annotations

from plone_client import PloneClient
from plone_client.config import PloneClientConfig

import pytest
import responses as resp_mock


BASE = "http://localhost:8080/Plone"


@pytest.fixture()
def cli() -> PloneClient:
    cfg = PloneClientConfig(
        base_url=BASE, token="test-token", max_retries=0, retry_backoff=0
    )
    return PloneClient(config=cfg)


@pytest.mark.unit
class TestUtilitiesManager:
    @resp_mock.activate
    def test_resolve_uid(self, cli: PloneClient) -> None:
        uid = "abc123def456abc123def456abc12345"
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@resolveuid/{uid}",
            json={"@id": f"{BASE}/my-doc", "title": "My Doc"},
        )
        result = cli.utilities.resolve_uid(uid)
        assert result["@id"] == f"{BASE}/my-doc"

    @resp_mock.activate
    def test_ids_returns_list(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/news/@ids",
            json=["article-1", "article-2", "article-3"],
        )
        result = cli.utilities.ids("/news")
        assert result == ["article-1", "article-2", "article-3"]

    @resp_mock.activate
    def test_ids_unwraps_items_key(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/news/@ids",
            json={"items": ["article-1", "article-2"]},
        )
        result = cli.utilities.ids("/news")
        assert result == ["article-1", "article-2"]

    @resp_mock.activate
    def test_search_principals(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@principals",
            json={"users": [{"id": "john"}], "groups": [{"id": "Reviewers"}]},
        )
        result = cli.utilities.search_principals("john")
        assert "users" in result

    @resp_mock.activate
    def test_user_schema(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@userschema",
            json={"properties": {"fullname": {"type": "string"}}},
        )
        result = cli.utilities.user_schema()
        assert "properties" in result

    @resp_mock.activate
    def test_expandable_fields_list(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/my-doc/@expandable-fields",
            json=["workflow", "sharing", "breadcrumbs"],
        )
        result = cli.utilities.expandable_fields("/my-doc")
        assert "breadcrumbs" in result

    @resp_mock.activate
    def test_expandable_fields_unwrap(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/my-doc/@expandable-fields",
            json={"items": ["workflow", "breadcrumbs"]},
        )
        result = cli.utilities.expandable_fields("/my-doc")
        assert result == ["workflow", "breadcrumbs"]

    @resp_mock.activate
    def test_navigation_root(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@navigation-root",
            json={"@id": BASE, "title": "My Site"},
        )
        result = cli.utilities.navigation_root()
        assert result["@id"] == BASE

    @resp_mock.activate
    def test_paste(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/news/@paste",
            json=[{"target": f"{BASE}/news/article-copy"}],
            status=200,
        )
        result = cli.utilities.paste("/news")
        assert isinstance(result, list)

    @resp_mock.activate
    def test_copy_to_clipboard(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/@clipboard",
            json={"op": "copy", "uids": ["uid-1"]},
        )
        result = cli.utilities.copy_to_clipboard("/", ["uid-1"])
        assert "op" in result

    @resp_mock.activate
    def test_site_config(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@config",
            json={"blocks": {}, "imageScales": {}},
        )
        result = cli.utilities.site_config()
        assert "blocks" in result

    @resp_mock.activate
    def test_update_site_config(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.PATCH,
            f"{BASE}/@config",
            json={"site_title": "My Plone"},
        )
        result = cli.utilities.update_site_config(site_title="My Plone")
        assert result["site_title"] == "My Plone"

    @resp_mock.activate
    def test_components(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@components",
            json={"contentType": {}, "editBlock": {}},
        )
        result = cli.utilities.components()
        assert "contentType" in result

    @resp_mock.activate
    def test_content_rules(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@content-rules",
            json={"items": [], "items_total": 0},
        )
        result = cli.utilities.content_rules()
        assert "items" in result

    @resp_mock.activate
    def test_sidebar(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/my-doc/@sidebar",
            json={"document": {"title": "My Doc"}},
        )
        result = cli.utilities.sidebar("/my-doc")
        assert "document" in result
