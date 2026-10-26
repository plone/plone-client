from . import check_request
from . import UID

import pytest


CASES = [
    (
        lambda c: c.comments.add("/doc", "Hi"),
        "POST",
        "/doc/@comments",
        [],
        {"text": "Hi"},
    ),
    (
        lambda c: c.comments.add("/doc", "Reply", reply_to="123"),
        "POST",
        "/doc/@comments/123",
        [],
        {"text": "Reply"},
    ),
    (
        lambda c: c.comments.update("/doc", "123", "New"),
        "PATCH",
        "/doc/@comments/123",
        [],
        {"text": "New"},
    ),
    (
        lambda c: c.comments.delete("/doc", "123"),
        "DELETE",
        "/doc/@comments/123",
        [],
        None,
    ),
    (lambda c: c.translations.get("/en/doc"), "GET", "/en/doc/@translations", [], None),
    (
        lambda c: c.translations.link("/en/doc", "/es/doc"),
        "POST",
        "/en/doc/@translations",
        [],
        {"id": "/es/doc"},
    ),
    (
        lambda c: c.translations.unlink("/en/doc", "es"),
        "DELETE",
        "/en/doc/@translations",
        [],
        {"language": "es"},
    ),
    (
        lambda c: c.translations.locate("/es/doc", "de"),
        "GET",
        "/es/doc/@translation-locator",
        [("target_language", "de")],
        None,
    ),
    (lambda c: c.aliases.list(), "GET", "/@aliases", [], None),
    (
        lambda c: c.aliases.list("/", query="/old", manual=True),
        "GET",
        "/@aliases",
        [("query", "/old"), ("manual", "true")],
        None,
    ),
    (
        lambda c: c.aliases.add("/doc", ["/a", "/b"]),
        "POST",
        "/doc/@aliases",
        [],
        {"items": [{"path": "/a"}, {"path": "/b"}]},
    ),
    (
        lambda c: c.aliases.add_redirects([
            {"path": "/old", "redirect-to": "/new", "datetime": "2026-05-05"}
        ]),
        "POST",
        "/@aliases",
        [],
        {"items": [{"path": "/old", "redirect-to": "/new", "datetime": "2026-05-05"}]},
    ),
    (
        lambda c: c.aliases.remove("/doc", "/a"),
        "DELETE",
        "/doc/@aliases",
        [],
        {"items": [{"path": "/a"}]},
    ),
    (lambda c: c.relations.stats(), "GET", "/@relations", [], None),
    (
        lambda c: c.relations.list(
            source="/doc", relation="relatedItems", only_broken=True, limit=100
        ),
        "GET",
        "/@relations",
        [
            ("source", "/doc"),
            ("relation", "relatedItems"),
            ("onlyBroken", "true"),
            ("max", "100"),
        ],
        None,
    ),
    (
        lambda c: c.relations.create([
            {"source": "/a", "target": "/b", "relation": "relatedItems"}
        ]),
        "POST",
        "/@relations",
        [],
        {"items": [{"source": "/a", "target": "/b", "relation": "relatedItems"}]},
    ),
    (
        lambda c: c.relations.delete([
            {"source": UID, "target": "/b", "relation": "relatedItems"}
        ]),
        "DELETE",
        "/@relations",
        [],
        {"items": [{"source": UID, "target": "/b", "relation": "relatedItems"}]},
    ),
    (
        lambda c: c.relations.delete(source="/doc", relation="relatedItems"),
        "DELETE",
        "/@relations",
        [],
        {"source": "/doc", "relation": "relatedItems"},
    ),
    (lambda c: c.relations.rebuild(), "POST", "/@relations/rebuild", [], None),
    (
        lambda c: c.relations.rebuild(flush=True),
        "POST",
        "/@relations/rebuild",
        [],
        {"flush": 1},
    ),
]


@pytest.mark.parametrize("call,method,path,params,body", CASES)
def test_requests(client, site, call, method, path, params, body):
    call(client)
    check_request(site, method, path, params, body)


def test_comments_list(client, site):
    site.add(
        "GET", "/doc/@comments", {"items": [{"comment_id": "1"}, {"comment_id": "2"}]}
    )
    assert [c["comment_id"] for c in client.comments.list("/doc")] == ["1", "2"]


def test_relations_delete_needs_a_filter(client):
    with pytest.raises(ValueError, match="Give relations"):
        client.relations.delete()
