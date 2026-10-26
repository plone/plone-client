from . import check_request

import pytest


CASES = [
    (lambda c: c.search.search(), "GET", "/@search", [], None),
    (
        lambda c: c.search.search(
            "/news",
            portal_type=["Document", "News Item"],
            review_state="published",
            text="plone",
            depth=1,
            sort_on="effective",
            sort_order="descending",
            metadata_fields=["UID", "modified"],
            b_size=10,
            b_start=20,
        ),
        "GET",
        "/news/@search",
        [
            ("portal_type", "Document"),
            ("portal_type", "News Item"),
            ("review_state", "published"),
            ("SearchableText", "plone"),
            ("path.depth", "1"),
            ("sort_on", "effective"),
            ("sort_order", "descending"),
            ("metadata_fields", "UID"),
            ("metadata_fields", "modified"),
            ("b_size", "10"),
            ("b_start", "20"),
        ],
        None,
    ),
    (
        lambda c: c.search.search(
            query={"created": {"query": "2026-01-01", "range": "min"}},
            Subject="plone",
            fullobjects=True,
        ),
        "GET",
        "/@search",
        [
            ("created.query", "2026-01-01"),
            ("created.range", "min"),
            ("fullobjects", "1"),
            ("Subject", "plone"),
        ],
        None,
    ),
    (lambda c: c.querystring.config(), "GET", "/@querystring", [], None),
    (
        lambda c: c.querystring.search(
            [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.any",
                    "v": ["Document"],
                }
            ],
            path="/news",
            sort_on="created",
            limit=10,
            metadata_fields="UID",
            fullobjects=True,
        ),
        "POST",
        "/news/@querystring-search",
        [],
        {
            "query": [
                {
                    "i": "portal_type",
                    "o": "plone.app.querystring.operation.selection.any",
                    "v": ["Document"],
                }
            ],
            "sort_on": "created",
            "limit": 10,
            "fullobjects": True,
            "metadata_fields": ["UID"],
        },
    ),
]


@pytest.mark.parametrize("call,method,path,params,body", CASES)
def test_requests(client, site, call, method, path, params, body):
    call(client)
    check_request(site, method, path, params, body)


def test_iter_and_count(client, site):
    site.add(
        "GET", "/news/@search", {"items": [{"id": 1}, {"id": 2}], "items_total": 7}
    )
    assert [item["id"] for item in client.search.iter("/news", limit=1)] == [1]
    assert ("b_size", "100") in site.params()
    assert client.search.count("/news", portal_type="Document") == 7
    assert ("b_size", "1") in site.params()
