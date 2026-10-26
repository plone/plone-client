from .. import DOCUMENT
from .. import SITE_URL

import base64
import httpx
import pytest


pytestmark = pytest.mark.usefixtures("cli_env")


def test_get_with_fields_anywhere(invoke, site):
    site.add("GET", "/news/doc", DOCUMENT)
    run = invoke("get", "/news/doc", "-f", "@id,title", "-c")
    assert run.exit_code == 0
    assert (
        run.stdout.strip() == f'{{"@id": "{SITE_URL}/news/doc", "title": "A document"}}'
    )
    assert (
        site.last.headers["Authorization"]
        == "Basic " + base64.b64encode(b"admin:secret").decode()
    )


def test_get_options(invoke, site):
    invoke(
        "get",
        "/news",
        "--expand",
        "breadcrumbs",
        "--expand",
        "navigation",
        "--no-items",
    )
    assert site.params() == [
        ("expand", "breadcrumbs,navigation"),
        ("include_items", "false"),
    ]


def test_not_found_is_json_on_stderr(invoke, site):
    site.add(
        "GET",
        "/missing",
        {"type": "NotFound", "message": "Resource not found"},
        status=404,
    )
    run = invoke("get", "/missing")
    assert run.exit_code == 5
    assert run.stdout == ""
    assert run.error["type"] == "NotFound"
    assert run.error["status_code"] == 404


def test_foreign_url_is_a_usage_error(invoke, site):
    run = invoke("get", "https://other.example.org/doc")
    assert run.exit_code == 2
    assert "is not a URL of" in run.error["message"]
    assert site.requests == []


def test_ls(invoke, site):
    site.add("GET", "/news/@search", {"items": [{"@id": f"{SITE_URL}/news/a"}]})
    run = invoke("ls", "/news", "--type", "Document", "--limit", "5")
    assert run.json == [{"@id": f"{SITE_URL}/news/a"}]
    assert ("portal_type", "Document") in site.params()


def test_search(invoke, site):
    site.add(
        "GET",
        "/news/@search",
        {"items": [{"@id": "a"}, {"@id": "b"}], "items_total": 2},
    )
    run = invoke(
        "search",
        "/news",
        "-q",
        "plone",
        "-t",
        "News Item",
        "--state",
        "published",
        "-i",
        "Subject=python",
        "-i",
        'created:={"query": "2026-01-01", "range": "min"}',
        "--sort-on",
        "effective",
        "--reverse",
        "--limit",
        "1",
    )
    assert run.exit_code == 0, run.stderr
    assert run.json == [{"@id": "a"}]
    assert site.params() == [
        ("Subject", "python"),
        ("created.query", "2026-01-01"),
        ("created.range", "min"),
        ("portal_type", "News Item"),
        ("review_state", "published"),
        ("SearchableText", "plone"),
        ("sort_on", "effective"),
        ("sort_order", "descending"),
        ("b_size", "1"),
    ]


def test_search_count(invoke, site):
    site.add("GET", "/@search", {"items": [], "items_total": 42})
    assert invoke("search", "--count").json == {"items_total": 42}


def test_create_adds_blocks_and_prints_summary(invoke, site):
    site.add("POST", "/news", DOCUMENT)
    run = invoke(
        "create",
        "/news",
        "Document",
        "--title",
        "A document",
        "--id",
        "doc",
        "--set",
        'subjects:=["a"]',
        "-d",
        '{"description": "D"}',
    )
    assert run.exit_code == 0, run.stderr
    assert run.json == {
        "@id": f"{SITE_URL}/news/doc",
        "@type": "Document",
        "UID": DOCUMENT["UID"],
        "id": "doc",
        "title": "A document",
        "review_state": "private",
    }
    body = site.body()
    assert body["@type"] == "Document"
    assert body["title"] == "A document"
    assert body["id"] == "doc"
    assert body["description"] == "D"
    assert body["subjects"] == ["a"]
    types = [body["blocks"][i]["@type"] for i in body["blocks_layout"]["items"]]
    assert types == ["title", "description"]


def test_create_and_publish(invoke, site):
    site.add("POST", "/news", DOCUMENT)
    site.add("GET", "/news/doc", {**DOCUMENT, "review_state": "published"})
    run = invoke(
        "create",
        "/news",
        "Document",
        "--title",
        "T",
        "--no-blocks",
        "--publish",
        "publish",
    )
    assert run.json["review_state"] == "published"
    paths = [(r.method, site.site_path(r)) for r in site.requests]
    assert paths == [
        ("POST", "/news"),
        ("POST", "/news/doc/@workflow/publish"),
        ("GET", "/news/doc"),
    ]
    assert "blocks" not in site.body(site.requests[0])


def test_update_dry_run(invoke, site):
    run = invoke("update", "/news/doc", "--title", "New", "-n")
    assert run.json == {
        "dry_run": True,
        "method": "PATCH",
        "url": f"{SITE_URL}/++api++/news/doc",
        "json": {"title": "New"},
    }
    assert site.requests == []


def test_update_needs_changes(invoke):
    run = invoke("update", "/news/doc")
    assert run.exit_code == 2
    assert "Nothing to change" in run.error["message"]


def test_read_only_refuses(invoke, site):
    run = invoke("--read-only", "update", "/news/doc", "--title", "New")
    assert run.exit_code == 7
    assert run.error["type"] == "PloneReadOnlyError"
    assert site.requests == []


def test_delete_needs_yes_without_terminal(invoke, site):
    run = invoke("delete", "/news/doc")
    assert run.exit_code == 2
    assert "pass --yes" in run.stderr
    assert site.requests == []


def test_delete(invoke, site):
    site.add("DELETE", "/news/a", status=204)
    site.add("DELETE", "/news/b", status=204)
    run = invoke("delete", "/news/a", "/news/b", "--yes")
    assert run.json == {"deleted": ["/news/a", "/news/b"], "dry_run": False}


def test_copy_and_move(invoke, site):
    invoke("copy", "/a", "/b", "--to", "/news")
    assert (site.site_path(site.last), site.body()) == (
        "/news/@copy",
        {"source": ["/a", "/b"]},
    )
    invoke("move", "/a", "--to", "/news")
    assert (site.site_path(site.last), site.body()) == (
        "/news/@move",
        {"source": ["/a"]},
    )


def test_order(invoke, site):
    site.add("GET", "/news/@search", {"items": [{"@id": "b"}, {"@id": "a"}]})
    run = invoke("order", "/news", "b", "top")
    assert run.json == ["b", "a"]
    assert site.body(site.requests[0]) == {"ordering": {"obj_id": "b", "delta": "top"}}
    invoke("order", "/news", "b", "-2")
    assert site.body(site.requests[2]) == {"ordering": {"obj_id": "b", "delta": -2}}
    invoke("order", "/news", "b", "down")
    assert site.body(site.requests[4]) == {"ordering": {"obj_id": "b", "delta": 1}}
    run = invoke("order", "/news", "b", "sideways")
    assert run.exit_code == 2
    assert "Not a valid delta" in run.error["message"]


def test_workflow_info_and_transition(invoke, site):
    site.add(
        "GET",
        "/doc/@workflow",
        {
            "state": {"id": "private", "title": "Private"},
            "transitions": [
                {"@id": f"{SITE_URL}/doc/@workflow/publish", "title": "Publish"}
            ],
            "history": [],
        },
    )
    run = invoke("workflow", "/doc")
    assert run.json == {
        "state": {"id": "private", "title": "Private"},
        "transitions": ["publish"],
        "history": [],
    }
    invoke("workflow", "/doc", "publish", "--comment", "Go", "--recursive")
    assert site.body() == {"comment": "Go", "include_children": True}


def test_blocks(invoke, site):
    site.add(
        "GET",
        "/doc",
        {
            **DOCUMENT,
            "blocks": {
                "1": {"@type": "title"},
                "2": {
                    "@type": "slate",
                    "plaintext": "Hello",
                    "value": [{"type": "link", "data": {"url": "/news"}}],
                },
            },
            "blocks_layout": {"items": ["1", "2"]},
        },
    )
    run = invoke("blocks", "/doc", "--links")
    assert run.json == [
        {"id": "1", "@type": "title"},
        {"id": "2", "@type": "slate", "text": "Hello", "links": ["/news"]},
    ]


def test_resolve_uid(invoke, site):
    uid = DOCUMENT["UID"]
    site.add("GET", "/@search", {"items": [{**DOCUMENT}]})
    run = invoke("resolve", f"uid:{uid}")
    assert run.json == {
        "path": "/news/doc",
        "url": f"{SITE_URL}/news/doc",
        "UID": uid,
        "@type": "Document",
        "title": "A document",
    }


def test_upload_and_download(invoke, site, tmp_path):
    source = tmp_path / "photo.png"
    source.write_bytes(b"PNGDATA")
    site.add(
        "POST",
        "/media",
        {**DOCUMENT, "@id": f"{SITE_URL}/media/photo.png", "@type": "Image"},
    )
    run = invoke("upload", "/media", str(source))
    assert run.exit_code == 0, run.stderr
    assert run.json[0]["@type"] == "Image"
    assert site.body()["image"]["filename"] == "photo.png"

    site.add(
        "GET",
        "/media/photo.png",
        {
            "@type": "Image",
            "image": {"filename": "photo.png", "content-type": "image/png"},
        },
    )
    site.add_callable(
        "GET",
        "/media/photo.png/@@download/image",
        lambda request: httpx.Response(200, content=b"PNGDATA"),
    )
    target = tmp_path / "out.png"
    run = invoke("download", "/media/photo.png", "-o", str(target))
    assert run.json == {"path": str(target), "size": 7, "content-type": "image/png"}
    assert target.read_bytes() == b"PNGDATA"


def test_upload_single_file_options(invoke, tmp_path):
    a, b = tmp_path / "a.txt", tmp_path / "b.txt"
    a.write_text("a")
    b.write_text("b")
    run = invoke("upload", "/media", str(a), str(b), "--title", "T")
    assert run.exit_code == 2
    assert "single file" in run.error["message"]
