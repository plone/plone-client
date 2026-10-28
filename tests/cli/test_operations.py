from .. import SITE_URL

import json
import pytest
import sys


pytestmark = pytest.mark.usefixtures("cli_env")

needs_html2blocks = pytest.mark.skipif(
    sys.version_info < (3, 12), reason="collective.html2blocks needs Python 3.12"
)


@needs_html2blocks
def test_create_page_from_stdin(invoke, site):
    site.add("POST", "/docs", {"@id": f"{SITE_URL}/docs/hello", "title": "Hello"})
    run = invoke("create-page", "/docs", "-", "--id", "hello", stdin="# Hello\n\nText.")
    assert run.exit_code == 0, run.stderr
    assert run.json["operation"] == "create_page"
    assert run.json["item"]["@id"] == f"{SITE_URL}/docs/hello"
    body = site.body()
    assert (body["@type"], body["id"], body["title"]) == ("Document", "hello", "Hello")


@needs_html2blocks
def test_create_page_from_an_html_file(invoke, site, tmp_path):
    source = tmp_path / "page.html"
    source.write_text("<h1>From HTML</h1><p>Text</p>")
    run = invoke("create-page", "/docs", str(source), "-n")
    assert run.exit_code == 0, run.stderr
    assert run.json["dry_run"] is True
    assert run.json["item"]["title"] == "From HTML"
    assert site.requests == []


def test_create_page_without_title(invoke, site):
    run = invoke("create-page", "/docs", "-", stdin="Only text")
    assert run.exit_code == 2
    assert "A title is needed" in run.error["message"]


@pytest.mark.parametrize(
    "options,lead",
    [((), "first"), (("--lead", "1"), 0), (("--no-lead",), None)],
)
def test_create_with_files_lead(invoke, site, tmp_path, monkeypatch, options, lead):
    seen = {}

    def fake(client, parent, portal_type, files, **kwargs):
        seen.update(kwargs, parent=parent, portal_type=portal_type, files=files)
        raise ValueError("stop")

    monkeypatch.setattr("plone_client.operations.create_with_files", fake)
    photo = tmp_path / "a.png"
    photo.write_bytes(b"png")
    run = invoke(
        "create-with-files",
        "/news",
        "News Item",
        str(photo),
        "--title",
        "Hi",
        *options,
    )
    assert run.exit_code == 2
    assert seen["lead_image"] == lead
    assert seen["data"] == {"title": "Hi"}
    assert seen["portal_type"] == "News Item"


def test_create_with_files(invoke, site, tmp_path):
    photo = tmp_path / "a.png"
    photo.write_bytes(b"\x89PNG")
    site.add("GET", "/@types/News Item", {"properties": {"preview_image_link": {}}})
    site.add("POST", "/news", {"@id": f"{SITE_URL}/news/hi", "title": "Hi"})
    site.add("POST", "/news/hi", {"@id": f"{SITE_URL}/news/hi/a.png", "UID": "u1"})
    site.add("GET", "/news/hi", {"@id": f"{SITE_URL}/news/hi", "title": "Hi"})
    run = invoke("create-with-files", "/news", "News Item", str(photo), "--title", "Hi")
    assert run.exit_code == 0, run.stderr
    assert [e["@id"] for e in run.json["created"]] == [
        f"{SITE_URL}/news/hi",
        f"{SITE_URL}/news/hi/a.png",
    ]
    assert run.json["changed"][0]["fields"] == {
        "preview_image_link": f"{SITE_URL}/news/hi/a.png"
    }


@pytest.mark.parametrize(
    "options,lead",
    [((), "first"), (("--lead", "2"), 1), (("--no-lead",), None)],
)
def test_create_page_lead_options(invoke, monkeypatch, tmp_path, options, lead):
    seen = {}

    def fake(client, parent, source, **kwargs):
        seen.update(kwargs, parent=parent)
        raise ValueError("stop")

    monkeypatch.setattr("plone_client.operations.create_page", fake)
    photo = tmp_path / "a.png"
    photo.write_bytes(b"png")
    other = tmp_path / "b.png"
    other.write_bytes(b"png")
    run = invoke(
        "create-page",
        "/docs",
        "-",
        "--file",
        str(photo),
        "--file",
        str(other),
        *options,
        stdin="# Hi",
    )
    assert run.exit_code == 2
    assert seen["files"] == [photo, other]
    assert seen["lead_image"] == lead
    assert seen["portal_type"] == "Document"


@needs_html2blocks
def test_create_page_with_files(invoke, site, tmp_path):
    photo = tmp_path / "a.png"
    photo.write_bytes(b"\x89PNG")
    site.add("GET", "/@types/Document", {"properties": {"preview_image_link": {}}})
    site.add("POST", "/docs", {"@id": f"{SITE_URL}/docs/hi", "title": "Hi"})
    site.add("POST", "/docs/hi", {"@id": f"{SITE_URL}/docs/hi/a.png", "UID": "u1"})
    run = invoke(
        "create-page",
        "/docs",
        "-",
        "--id",
        "hi",
        "--file",
        str(photo),
        stdin="# Hi\n\nText.",
    )
    assert run.exit_code == 0, run.stderr
    assert [e["@id"] for e in run.json["created"]] == [
        f"{SITE_URL}/docs/hi",
        f"{SITE_URL}/docs/hi/a.png",
    ]
    assert run.json["changed"][0]["fields"] == {
        "preview_image_link": f"{SITE_URL}/docs/hi/a.png"
    }


def test_operation_failure_reports_what_was_done(invoke, site, tmp_path):
    (tmp_path / "a.txt").write_text("a")
    (tmp_path / "b.txt").write_text("b")
    site.add("GET", "/docs", {})
    site.add("POST", "/docs", {"@id": f"{SITE_URL}/docs/a.txt"})
    site.add("POST", "/docs", {"message": "Not allowed"}, status=403)
    run = invoke("upload-tree", str(tmp_path), "/docs")
    assert run.exit_code == 4
    assert run.error["status_code"] == 403
    result = json.loads(run.stderr)["result"]
    assert result["operation"] == "upload_tree"
    assert [e["@id"] for e in result["created"]] == [f"{SITE_URL}/docs/a.txt"]


def test_upload_tree_dry_run(invoke, site, tmp_path):
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "a.txt").write_text("a")
    run = invoke(
        "upload-tree", str(tmp_path), "/docs", "--dry-run", "--publish", "publish"
    )
    assert run.exit_code == 0, run.stderr
    assert [e["@id"] for e in run.json["created"]] == [
        f"{SITE_URL}/docs/sub",
        f"{SITE_URL}/docs/sub/a.txt",
    ]
    assert [r.method for r in site.requests] == ["GET"]


def test_block_types(invoke, site):
    site.add("POST", "/@login", {"token": "t"})
    site.add("GET", "/Plone/@blocks-schema", status=404)
    site.add("GET", "/Plone/@blocks-schema/teaser", status=404)
    run = invoke("block-types")
    assert run.exit_code == 0, run.stderr
    assert run.json["source"] == "builtin"
    run = invoke("block-types", "teaser", "-f", "id,source")
    assert run.json == {"id": "teaser", "source": "builtin"}
    run = invoke("block-types", "--markdown")
    assert "(`slate`)" in run.stdout


def test_block_types_for_an_item(invoke, site):
    site.add("POST", "/@login", {"token": "t"})
    site.add("GET", "/Plone/news/@blocks-schema", {"items": [], "items_total": 0})
    run = invoke("block-types", "--for", "/news")
    assert run.json == {"items": [], "items_total": 0, "source": "site"}


def test_frontend_url_from_the_environment(invoke, site, monkeypatch):
    monkeypatch.setenv("PLONE_CLIENT_FRONTEND_URL", "http://www.plone.test")
    site.add("POST", "/@login", {"token": "t"})
    invoke("block-types")
    assert str(site.last.url) == "http://www.plone.test/@blocks-schema"


def test_mcp_needs_the_extra(invoke, monkeypatch):
    # what importing the module does without the mcp package
    monkeypatch.setitem(sys.modules, "plone_client.mcp_server", None)
    run = invoke("mcp")
    assert run.exit_code == 3
    assert "'mcp' extra" in run.error["message"]


def test_mcp_serves_the_client(invoke, monkeypatch):
    served = []
    monkeypatch.setattr("plone_client.mcp_server.serve", served.append)
    run = invoke("--read-only", "mcp", "-n")
    assert run.exit_code == 0, run.stderr
    (client,) = served
    assert (client.url, client.read_only, client.dry_run) == (SITE_URL, True, True)


def _profiles(invoke, *names):
    for name in names:
        extra = ["--read-only"] if name == "prod" else []
        run = invoke(
            "profile",
            "add",
            name,
            "--url",
            f"http://{name}.test/Plone",
            "--username",
            "editor",
            "--password-stdin",
            *extra,
            stdin="secret\n",
        )
        assert run.exit_code == 0, run.stderr


@pytest.fixture
def served(monkeypatch):
    found = []
    monkeypatch.setattr("plone_client.mcp_server.serve", found.append)
    return found


def test_mcp_serves_several_sites(invoke, memory_keyring, served):
    _profiles(invoke, "blog", "docs", "prod")
    invoke("profile", "group-set", "work", "prod", "docs")
    run = invoke(
        "--dry-run", "mcp", "--site", "blog", "--group", "work", "--site", "docs"
    )
    assert run.exit_code == 0, run.stderr
    (sites,) = served
    assert sites.names == ["blog", "docs", "prod"]
    assert [s.read_only for s in sites] == [False, False, True]
    assert sites.dry_run is True
    client = sites.client("prod")
    assert (client.url, client.read_only, client.dry_run) == (
        "http://prod.test/Plone",
        True,
        True,
    )


def test_mcp_serves_every_site(invoke, memory_keyring, served):
    _profiles(invoke, "docs", "blog")
    run = invoke("--read-only", "mcp", "--all")
    assert run.exit_code == 0, run.stderr
    (sites,) = served
    assert sites.names == ["blog", "docs"]
    assert not sites.writable


@pytest.mark.parametrize(
    "args,message",
    [
        (["-p", "blog", "mcp", "--site", "blog"], "not both"),
        (["mcp", "--group", "nope"], "Unknown group 'nope'"),
        (["mcp", "--site", "nope"], "Unknown profile 'nope'"),
    ],
)
def test_mcp_site_errors(invoke, memory_keyring, served, args, message):
    _profiles(invoke, "blog")
    run = invoke(*args)
    assert run.exit_code == 3
    assert message in run.error["message"]
    assert served == []
