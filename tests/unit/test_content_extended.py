"""Extended unit tests for ContentManager — locking, aliases, ordering, blocks."""

from __future__ import annotations

from plone_client import PloneClient
from plone_client.config import PloneClientConfig

import pytest
import responses as resp_mock


BASE = "http://localhost:8080/Plone"


@pytest.fixture()
def cli() -> PloneClient:
    return PloneClient(
        config=PloneClientConfig(
            base_url=BASE, token="tok", max_retries=0, retry_backoff=0
        )
    )


@pytest.mark.unit
class TestContentLocking:
    @resp_mock.activate
    def test_lock(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/my-doc/@lock",
            json={"locked": True, "stealable": True},
        )
        result = cli.content.lock("/my-doc")
        assert result["locked"] is True

    @resp_mock.activate
    def test_lock_info(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/my-doc/@lock",
            json={"locked": True, "creator": "admin", "stealable": True},
        )
        result = cli.content.lock_info("/my-doc")
        assert result["creator"] == "admin"

    @resp_mock.activate
    def test_unlock(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.DELETE,
            f"{BASE}/my-doc/@lock",
            json={"locked": False},
        )
        result = cli.content.unlock("/my-doc")
        assert result["locked"] is False


@pytest.mark.unit
class TestContentAliases:
    @resp_mock.activate
    def test_get_aliases(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/my-doc/@aliases",
            json={"items": [{"path": "/old-path"}]},
        )
        result = cli.content.get_aliases("/my-doc")
        assert result["items"][0]["path"] == "/old-path"

    @resp_mock.activate
    def test_add_alias(self, cli: PloneClient) -> None:
        import json

        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/my-doc/@aliases",
            json={"items": [{"path": "/old-path"}]},
            status=201,
        )
        cli.content.add_alias("/my-doc", "/old-path")
        body = json.loads(resp_mock.calls[0].request.body)
        assert body["items"][0]["path"] == "/old-path"

    @resp_mock.activate
    def test_remove_alias(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.DELETE,
            f"{BASE}/my-doc/@aliases",
            status=204,
        )
        cli.content.remove_alias("/my-doc", "/old-path")


@pytest.mark.unit
class TestContentNavigation:
    @resp_mock.activate
    def test_navigation_default_depth(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@navigation",
            json={"items": []},
        )
        cli.content.navigation()
        url = resp_mock.calls[0].request.url
        assert "depth=1" in url

    @resp_mock.activate
    def test_navigation_custom_depth(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@navigation",
            json={"items": []},
        )
        cli.content.navigation(depth=3)
        assert "depth=3" in resp_mock.calls[0].request.url

    @resp_mock.activate
    def test_breadcrumbs(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/news/article/@breadcrumbs",
            json={
                "items": [{"title": "Home"}, {"title": "News"}, {"title": "Article"}]
            },
        )
        result = cli.content.breadcrumbs("/news/article")
        assert len(result["items"]) == 3

    @resp_mock.activate
    def test_contextnavigation(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/news/@contextnavigation",
            json={"items": []},
        )
        result = cli.content.contextnavigation("/news")
        assert "items" in result


@pytest.mark.unit
class TestContentWorkflow:
    @resp_mock.activate
    def test_workflow_lists_transitions(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/my-doc/@workflow",
            json={
                "transitions": [
                    {"@id": f"{BASE}/my-doc/@workflow/publish", "title": "Publish"}
                ],
                "state": {"id": "private"},
            },
        )
        result = cli.content.workflow("/my-doc")
        assert len(result["transitions"]) == 1

    @resp_mock.activate
    def test_transition_with_options(self, cli: PloneClient) -> None:
        import json

        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/my-doc/@workflow/publish",
            json={"review_state": "published"},
        )
        cli.content.transition(
            "/my-doc",
            "publish",
            comment="Approved",
            effective="2026-01-01T00:00:00",
            include_children=True,
        )
        body = json.loads(resp_mock.calls[0].request.body)
        assert body["comment"] == "Approved"
        assert body["effective"] == "2026-01-01T00:00:00"
        assert body["include_children"] is True


@pytest.mark.unit
class TestContentCopyMove:
    @resp_mock.activate
    def test_copy_sends_target(self, cli: PloneClient) -> None:
        import json

        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/news/article/@copy",
            json=[{"source": "/news/article", "target": "/archive/article"}],
        )
        cli.content.copy("/news/article", "/archive")
        body = json.loads(resp_mock.calls[0].request.body)
        assert body["target"] == "/archive"

    @resp_mock.activate
    def test_move_sends_target(self, cli: PloneClient) -> None:
        import json

        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/news/article/@move",
            json=[{"source": "/news/article", "target": "/archive/article"}],
        )
        cli.content.move("/news/article", "/archive")
        body = json.loads(resp_mock.calls[0].request.body)
        assert body["target"] == "/archive"


@pytest.mark.unit
class TestContentReplace:
    @resp_mock.activate
    def test_replace_uses_put(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.PUT,
            f"{BASE}/my-doc",
            json={"@type": "Document", "title": "Replaced"},
        )
        payload = {"@type": "Document", "title": "Replaced", "description": ""}
        result = cli.content.replace("/my-doc", payload)
        assert result["title"] == "Replaced"
