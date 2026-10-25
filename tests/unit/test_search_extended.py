"""Extended unit tests for SearchManager — query building and edge cases."""

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
class TestSearchQueryBuilding:
    @resp_mock.activate
    def test_empty_query_uses_defaults(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@search",
            json={"items": [], "items_total": 0},
        )
        cli.search.search()
        url = resp_mock.calls[0].request.url
        assert "b_size=25" in url
        assert "b_start=0" in url

    @resp_mock.activate
    def test_sort_params_included(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@search",
            json={"items": [], "items_total": 0},
        )
        cli.search.search(sort_on="created", sort_order="descending")
        url = resp_mock.calls[0].request.url
        assert "sort_on=created" in url
        assert "sort_order=descending" in url

    @resp_mock.activate
    def test_path_scoping(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@search",
            json={"items": [], "items_total": 0},
        )
        cli.search.search(path="/news")
        url = resp_mock.calls[0].request.url
        assert "path.query" in url
        assert "path.depth" in url

    @resp_mock.activate
    def test_fullobjects_flag(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@search",
            json={"items": [], "items_total": 0},
        )
        cli.search.search(fullobjects=True)
        url = resp_mock.calls[0].request.url
        assert "fullobjects=1" in url

    @resp_mock.activate
    def test_extra_params_forwarded(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@search",
            json={"items": [], "items_total": 0},
        )
        cli.search.search({"portal_type": "Document"}, review_state="published")
        url = resp_mock.calls[0].request.url
        assert "review_state=published" in url

    @resp_mock.activate
    def test_querystring_options(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@querystring",
            json={"indexes": {}},
        )
        result = cli.search.querystring_options()
        assert "indexes" in result

    @resp_mock.activate
    def test_querystring_search_payload(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.POST,
            f"{BASE}/@querystring-search",
            json={"items": [], "items_total": 0},
        )
        import json

        query = [
            {
                "i": "portal_type",
                "o": "plone.app.querystring.operation.selection.any",
                "v": ["Document"],
            }
        ]
        cli.search.querystring(query, b_size=10, sort_on="created")
        body = json.loads(resp_mock.calls[0].request.body)
        assert body["query"] == query
        assert body["b_size"] == 10

    @resp_mock.activate
    def test_iterate_stops_when_exhausted(self, cli: PloneClient) -> None:
        """iterate() must stop exactly when b_start >= items_total."""
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@search",
            json={"items": [{"@id": "/a"}], "items_total": 1},
        )
        items = list(cli.search.iterate(b_size=10))
        assert len(items) == 1
        assert len(resp_mock.calls) == 1  # only one HTTP call

    @resp_mock.activate
    def test_iterate_three_pages(self, cli: PloneClient) -> None:
        for i in range(3):
            resp_mock.add(
                resp_mock.GET,
                f"{BASE}/@search",
                json={
                    "items": [{"@id": f"/{i}"}],
                    "items_total": 3,
                },
            )
        items = list(cli.search.iterate(b_size=1))
        assert len(items) == 3
        assert len(resp_mock.calls) == 3

    @resp_mock.activate
    def test_iterate_empty_result(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@search",
            json={"items": [], "items_total": 0},
        )
        assert list(cli.search.iterate()) == []


@pytest.mark.unit
class TestSearchManagerDefaultPath:
    @resp_mock.activate
    def test_default_path_not_added_to_params(self, cli: PloneClient) -> None:
        """When path='/' (default), path.query should NOT be added."""
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@search",
            json={"items": [], "items_total": 0},
        )
        cli.search.search()
        url = resp_mock.calls[0].request.url
        assert "path.query" not in url

    @resp_mock.activate
    def test_non_root_path_added(self, cli: PloneClient) -> None:
        resp_mock.add(
            resp_mock.GET,
            f"{BASE}/@search",
            json={"items": [], "items_total": 0},
        )
        cli.search.search(path="/news")
        url = resp_mock.calls[0].request.url
        assert "path.query" in url
