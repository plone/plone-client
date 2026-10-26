from .. import SITE_URL
from . import check_request

import pytest


CASES = [
    (lambda c: c.types.list("/news"), "GET", "/news/@types", [], None),
    (lambda c: c.types.get("Document"), "GET", "/@types/Document", [], None),
    (
        lambda c: c.types.get_field("Document", "author_email"),
        "GET",
        "/@types/Document/author_email",
        [],
        None,
    ),
    (
        lambda c: c.types.add_field(
            "Document", {"factory": "Email", "title": "Author email"}
        ),
        "POST",
        "/@types/Document",
        [],
        {"factory": "Email", "title": "Author email"},
    ),
    (
        lambda c: c.types.update("Document", {"title": "Email"}, name="author_email"),
        "PATCH",
        "/@types/Document/author_email",
        [],
        {"title": "Email"},
    ),
    (
        lambda c: c.types.replace("Document", {"fieldsets": []}),
        "PUT",
        "/@types/Document",
        [],
        {"fieldsets": []},
    ),
    (
        lambda c: c.types.delete_field("Document", "author_email"),
        "DELETE",
        "/@types/Document/author_email",
        [],
        None,
    ),
    (lambda c: c.vocabularies.list(), "GET", "/@vocabularies", [], None),
    (
        lambda c: c.vocabularies.get(
            "plone.app.vocabularies.ReallyUserFriendlyTypes",
            title="doc",
            sort_on="title",
            b_size=-1,
        ),
        "GET",
        "/@vocabularies/plone.app.vocabularies.ReallyUserFriendlyTypes",
        [("title", "doc"), ("sort_on", "title"), ("b_size", "-1")],
        None,
    ),
    (
        lambda c: c.vocabularies.get("v", token=["Document", "Event"]),
        "GET",
        "/@vocabularies/v",
        [("tokens", "Document"), ("tokens", "Event")],
        None,
    ),
    (
        lambda c: c.vocabularies.get("v", token="Document"),
        "GET",
        "/@vocabularies/v",
        [("token", "Document")],
        None,
    ),
    (
        lambda c: c.vocabularies.source("/doc", "field"),
        "GET",
        "/doc/@sources/field",
        [],
        None,
    ),
    (
        lambda c: c.vocabularies.querysource("/doc", "field", "abc"),
        "GET",
        "/doc/@querysources/field",
        [("query", "abc")],
        None,
    ),
]


@pytest.mark.parametrize("call,method,path,params,body", CASES)
def test_requests(client, site, call, method, path, params, body):
    call(client)
    check_request(site, method, path, params, body)


def test_addable(client, site):
    site.add(
        "GET",
        "/news/@types",
        [
            {"@id": f"{SITE_URL}/@types/Document", "addable": True},
            {"@id": f"{SITE_URL}/@types/Folder", "addable": False},
            {"@id": f"{SITE_URL}/@types/News Item", "addable": True},
        ],
    )
    assert client.types.addable("/news") == ["Document", "News Item"]


def test_vocabulary_iter(client, site):
    site.add("GET", "/@vocabularies/v", {"items": [{"token": "a"}, {"token": "b"}]})
    assert [t["token"] for t in client.vocabularies.iter("v")] == ["a", "b"]
