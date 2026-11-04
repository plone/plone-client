from .. import DOCUMENT
from .. import SITE_URL
from . import check_request
from . import UID
from plone_client import blocks
from plone_client.exceptions import PloneNotFoundError

import pytest


CASES = [
    (lambda c: c.content.get("/news"), "GET", "/news", [], None),
    (
        lambda c: c.content.get(
            "/news", expand=["breadcrumbs", "navigation"], fullobjects=True
        ),
        "GET",
        "/news",
        [("expand", "breadcrumbs,navigation"), ("fullobjects", "1")],
        None,
    ),
    (
        lambda c: c.content.get("/news", include_items=False, version=2),
        "GET",
        "/news",
        [("include_items", "false"), ("version", "2")],
        None,
    ),
    (
        lambda c: c.content.create("/news", "Document", {"title": "T"}, id="t"),
        "POST",
        "/news",
        [],
        {"@type": "Document", "title": "T", "id": "t"},
    ),
    (lambda c: c.content.delete("/news/t"), "DELETE", "/news/t", [], None),
    (
        lambda c: c.content.copy("/front-page", "/news"),
        "POST",
        "/news/@copy",
        [],
        {"source": ["/front-page"]},
    ),
    (
        lambda c: c.content.move(["/a", "/b"], "/news"),
        "POST",
        "/news/@move",
        [],
        {"source": ["/a", "/b"]},
    ),
    (
        lambda c: c.content.order(
            "/news", "item-3", "top", subset_ids=["item-1", "item-3"]
        ),
        "PATCH",
        "/news",
        [],
        {
            "ordering": {
                "obj_id": "item-3",
                "delta": "top",
                "subset_ids": ["item-1", "item-3"],
            }
        },
    ),
    (
        lambda c: c.content.order("/news", "item-3", -1),
        "PATCH",
        "/news",
        [],
        {"ordering": {"obj_id": "item-3", "delta": -1}},
    ),
    (
        lambda c: c.content.sort("/news", "modified", "descending"),
        "PATCH",
        "/news",
        [],
        {"sort": {"on": "modified", "order": "descending"}},
    ),
    (lambda c: c.content.lock("/doc"), "POST", "/doc/@lock", [], {"stealable": True}),
    (
        lambda c: c.content.lock("/doc", stealable=False, timeout=60),
        "POST",
        "/doc/@lock",
        [],
        {"stealable": False, "timeout": 60},
    ),
    (lambda c: c.content.unlock("/doc"), "DELETE", "/doc/@lock", [], None),
    (
        lambda c: c.content.unlock("/doc", force=True),
        "DELETE",
        "/doc/@lock",
        [],
        {"force": True},
    ),
    (lambda c: c.content.refresh_lock("/doc"), "PATCH", "/doc/@lock", [], None),
    (lambda c: c.content.lock_info("/doc"), "GET", "/doc/@lock", [], None),
    (
        lambda c: c.content.link_integrity([UID, "f" * 32]),
        "GET",
        "/@linkintegrity",
        [("uids", UID), ("uids", "f" * 32)],
        None,
    ),
]


@pytest.mark.parametrize("call,method,path,params,body", CASES)
def test_requests(client, site, call, method, path, params, body):
    call(client)
    check_request(site, method, path, params, body)


def test_update_asks_for_the_representation(client, site):
    site.add("PATCH", "/doc", DOCUMENT)
    assert client.content.update("/doc", {"title": "New"}, description="D") == DOCUMENT
    assert site.body() == {"title": "New", "description": "D"}
    assert site.last.headers["Prefer"] == "return=representation"


def test_update_without_representation_and_with_lock(client, site):
    site.add("PATCH", "/doc", status=204)
    assert (
        client.content.update(
            "/doc", title="New", representation=False, lock_token="tok"
        )
        is None
    )
    assert "Prefer" not in site.last.headers
    assert site.last.headers["Lock-Token"] == "tok"


@pytest.mark.parametrize("ref", [f"uid:{UID}", f"../resolveuid/{UID}"])
def test_resolve_uid(client, site, ref):
    site.add("GET", "/@search", {"items": [{"@id": f"{SITE_URL}/news/doc"}]})
    assert client.content.resolve(ref) == "/news/doc"
    assert site.params() == [("UID", UID)]


def test_resolve_plain_path_sends_nothing(client, site):
    assert client.content.resolve(f"{SITE_URL}/news/") == "/news"
    assert site.requests == []


def test_get_by_uid(client, site):
    site.add("GET", "/@search", {"items": [{"@id": f"{SITE_URL}/news/doc"}]})
    site.add("GET", "/news/doc", DOCUMENT)
    assert client.content.get(f"uid:{UID}") == DOCUMENT


def test_find_by_uid_not_found(client, site):
    site.add("GET", "/@search", {"items": [], "items_total": 0})
    with pytest.raises(PloneNotFoundError, match=f"No item with UID {UID}"):
        client.content.find_by_uid(UID)


def test_uid_works_in_every_manager(client, site):
    site.add("GET", "/@search", {"items": [{"@id": f"{SITE_URL}/news/doc"}]})
    client.workflow.transition(f"uid:{UID}", "publish")
    check_request(site, "POST", "/news/doc/@workflow/publish", [], None)


def test_children(client, site):
    site.add("GET", "/news/@search", {"items": [{"id": "a"}, {"id": "b"}]})
    children = list(client.content.children("/news", portal_type="Document", limit=5))
    assert [child["id"] for child in children] == ["a", "b"]
    check_request(
        site,
        "GET",
        "/news/@search",
        [
            ("path.depth", "1"),
            ("sort_on", "getObjPositionInParent"),
            ("portal_type", "Document"),
            ("b_size", "100"),
        ],
        None,
    )


def test_exists(client, site):
    site.add("GET", "/news", {})
    assert client.content.exists("/news") is True


@pytest.fixture
def types_at_root(site):
    entries = [
        {"@id": f"{SITE_URL}/@types/Folder", "addable": False},
        {"@id": f"{SITE_URL}/@types/Document", "addable": True},
    ]
    site.add("GET", "/@types", entries)


@pytest.mark.usefixtures("types_at_root")
def test_dry_run_warns_about_a_refused_type(client_factory):
    client = client_factory(dry_run=True)
    answer = client.content.create("/", "Folder", title="News")
    assert answer["dry_run"] is True
    assert answer["warning"] == (
        "The site would refuse this: Folder cannot be added in /. It can add: Document."
    )


@pytest.mark.usefixtures("types_at_root")
def test_dry_run_does_not_warn_about_an_addable_type(client_factory):
    client = client_factory(dry_run=True)
    answer = client.content.create("/", "Document", title="News")
    assert "warning" not in answer


def test_dry_run_warns_when_nothing_can_be_added(client_factory, site):
    site.add("GET", "/news/@types", [])
    client = client_factory(dry_run=True)
    answer = client.content.create("/news", "Document", title="News")
    assert answer["warning"].endswith("It can add: nothing.")


def test_dry_run_does_not_warn_when_the_site_cannot_say(client_factory, site):
    site.add("GET", "/planned/@types", {"message": "Not found"}, status=404)
    client = client_factory(dry_run=True)
    answer = client.content.create("/planned", "Document", title="News")
    assert answer["dry_run"] is True
    assert "warning" not in answer


def test_real_create_does_not_ask_for_types(client, site):
    site.add("POST", "/", {"@id": f"{SITE_URL}/news"}, status=201)
    client.content.create("/", "Document", title="News")
    assert [request.method for request in site.requests] == ["POST"]


DOCUMENT_SCHEMA = {
    "properties": {"title": {}, "description": {}, "blocks": {}, "blocks_layout": {}}
}
TEXT = {"@type": "slate", "plaintext": "Hi"}


@pytest.fixture
def document_schema(site):
    site.add("GET", "/@types/Document", DOCUMENT_SCHEMA)


@pytest.mark.usefixtures("types_at_root", "document_schema")
def test_dry_run_warns_about_a_list_of_blocks(client_factory):
    client = client_factory(dry_run=True)
    answer = client.content.create("/", "Document", title="News", blocks=[TEXT])
    assert answer["warning"].startswith(
        "The site would refuse this: blocks must be a mapping of block ids"
    )


@pytest.mark.usefixtures("types_at_root", "document_schema")
def test_dry_run_warns_about_a_block_without_type(client_factory):
    client = client_factory(dry_run=True)
    answer = client.content.create(
        "/",
        "Document",
        blocks={"a": {"plaintext": "Hi"}},
        blocks_layout={"items": ["a"]},
    )
    assert answer["warning"] == "The site would refuse this: blocks without @type: a."


@pytest.mark.usefixtures("types_at_root", "document_schema")
def test_dry_run_warns_about_a_layout_that_misses_blocks(client_factory):
    client = client_factory(dry_run=True)
    answer = client.content.create("/", "Document", blocks={"a": TEXT, "b": TEXT})
    assert "blocks_layout.items must list the ids in blocks" in answer["warning"]


@pytest.mark.usefixtures("types_at_root", "document_schema")
def test_dry_run_accepts_built_blocks(client_factory):
    client = client_factory(dry_run=True)
    answer = client.content.create(
        "/", "Document", title="News", **blocks.build(blocks.title(), TEXT)
    )
    assert "warning" not in answer


@pytest.mark.usefixtures("types_at_root", "document_schema")
def test_dry_run_warns_about_fields_the_type_lacks(client_factory):
    client = client_factory(dry_run=True)
    answer = client.content.create(
        "/", "Document", id="news", title="News", image="x", text="y"
    )
    assert answer["warning"] == (
        "The site would ignore fields that Document does not have: image, text."
    )


def test_dry_run_joins_its_warnings(client_factory, site):
    site.add("GET", "/@types", [{"@id": f"{SITE_URL}/@types/Folder", "addable": False}])
    site.add("GET", "/@types/Folder", {"properties": {"title": {}}})
    client = client_factory(dry_run=True)
    answer = client.content.create("/", "Folder", title="News", blocks=[TEXT])
    assert answer["warning"].count("The site would") == 3


def test_dry_run_update_warns_about_blocks(client_factory):
    client = client_factory(dry_run=True)
    answer = client.content.update("/news", blocks=[TEXT])
    assert answer["warning"].startswith("The site would refuse this: blocks must")


def test_dry_run_update_without_blocks_has_no_warning(client_factory):
    client = client_factory(dry_run=True)
    answer = client.content.update("/news", title="News")
    assert "warning" not in answer
