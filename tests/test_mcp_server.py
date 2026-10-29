from . import SITE_URL
from mcp.server.mcpserver.exceptions import ToolError
from pathlib import Path
from plone_client import mcp_server
from plone_client import PloneClient
from plone_client.exceptions import PloneConfigurationError
from plone_client.profiles import Profile

import asyncio
import json
import pytest


READ_TOOLS = {
    "block_types",
    "call_service",
    "content_types",
    "get_content",
    "get_navigation",
    "list_blocks",
    "list_children",
    "search",
    "site_info",
}
WRITE_TOOLS = {
    "add_blocks",
    "copy_content",
    "create_content",
    "create_content_with_files",
    "delete_content",
    "move_content",
    "remove_blocks",
    "run_transition",
    "set_blocks",
    "update_block",
    "update_content",
    "upload_tree",
}
if mcp_server.has_html2blocks():
    WRITE_TOOLS.add("create_page")


def tools(server):
    return {tool.name: tool for tool in asyncio.run(server.list_tools())}


def call(server, name, **arguments):
    """Call a tool and return its structured result, or its text."""
    result = asyncio.run(server.call_tool(name, arguments))
    assert not result.is_error
    if result.structured_content is not None:
        if set(result.structured_content) == {"result"}:
            return result.structured_content["result"]
        return result.structured_content
    return result.content[0].text


def tool_error(server, name, **arguments):
    """Call a tool that fails and return the JSON of its error."""
    with pytest.raises(ToolError) as info:
        asyncio.run(server.call_tool(name, arguments))
    return json.loads(str(info.value).split(": ", 1)[1])


def test_tools(client):
    found = tools(mcp_server.build_server(client))
    assert set(found) == READ_TOOLS | WRITE_TOOLS
    assert found["get_content"].annotations.read_only_hint is True
    assert found["delete_content"].annotations.destructive_hint is True
    assert found["create_content"].annotations.destructive_hint is False
    assert all(tool.description for tool in found.values())


@pytest.mark.parametrize(
    "name,idempotent",
    [
        ("update_content", True),
        ("run_transition", False),
        ("move_content", False),
        ("call_service", False),
    ],
)
def test_idempotent_hint(client, name, idempotent):
    annotations = tools(mcp_server.build_server(client))[name].annotations
    assert annotations.idempotent_hint is idempotent


def test_read_only_server_has_no_write_tools(client_factory):
    server = mcp_server.build_server(client_factory(read_only=True))
    assert set(tools(server)) == READ_TOOLS
    assert "This server is read-only." in server.instructions


def test_dry_run_is_announced(client_factory):
    server = mcp_server.build_server(client_factory(dry_run=True))
    assert "This server is in a dry run." in server.instructions


def test_create_page_needs_html2blocks(client, monkeypatch):
    monkeypatch.setattr(mcp_server, "find_spec", lambda name: None)
    assert "create_page" not in tools(mcp_server.build_server(client))


def test_create_page_needs_the_collective_package(client, monkeypatch):
    def find_spec(name):
        raise ModuleNotFoundError("No module named 'collective'")

    monkeypatch.setattr(mcp_server, "find_spec", find_spec)
    assert not mcp_server.has_html2blocks()
    assert "create_page" not in tools(mcp_server.build_server(client))


def test_arguments_have_descriptions(client):
    schema = tools(mcp_server.build_server(client))["get_content"].input_schema
    assert "Site path" in schema["properties"]["path"]["description"]


def test_get_content(client, site):
    site.add("GET", "/news", {"@id": f"{SITE_URL}/news", "title": "News", "x": 1})
    server = mcp_server.build_server(client)
    assert call(server, "get_content", path="/news", fields=["title"]) == {
        "title": "News"
    }
    assert site.params() == [("include_items", "false")]


def test_errors_reach_the_model_as_json(client, site):
    site.add("GET", "/gone", {"type": "NotFound", "message": "Gone"}, status=404)
    error = tool_error(mcp_server.build_server(client), "get_content", path="/gone")
    assert error["error"]["status_code"] == 404
    assert error["error"]["message"] == "Gone"


def test_value_errors_reach_the_model(client):
    error = tool_error(
        mcp_server.build_server(client),
        "upload_tree",
        local_path="/nonexistent/folder",
        parent="/",
    )
    missing = Path("/nonexistent/folder")
    assert error == {
        "error": {"type": "ValueError", "message": f"Not a folder: {missing}"}
    }


def test_operation_errors_carry_the_result(client, site, tmp_path):
    (tmp_path / "a.txt").write_text("a")
    site.add("GET", "/docs", {"is_folderish": True})
    site.add("POST", "/docs", {"message": "Not allowed"}, status=400)
    error = tool_error(
        mcp_server.build_server(client),
        "upload_tree",
        local_path=str(tmp_path),
        parent="/docs",
    )
    assert error["error"]["status_code"] == 400
    assert error["result"]["operation"] == "upload_tree"
    assert [r["status"] for r in error["result"]["requests"]] == [200, 400]


def test_list_children_and_search(client, site):
    site.add("GET", "/news/@search", {"items": [{"@id": "a"}], "items_total": 1})
    site.add("GET", "/@search", {"items": [{"@id": "b"}], "items_total": 1})
    server = mcp_server.build_server(client)
    assert call(server, "list_children", path="/news") == {
        "items": [{"@id": "a"}],
        "items_count": 1,
    }
    found = call(
        server,
        "search",
        text="plone",
        portal_type=["News Item"],
        query={"Subject": "x"},
        sort_on="modified",
        descending=True,
        limit=5,
    )
    assert found["items"] == [{"@id": "b"}]
    params = dict(site.params())
    assert params["SearchableText"] == "plone"
    assert params["sort_order"] == "descending"
    assert params["Subject"] == "x"


def test_content_types(client, site):
    site.add(
        "GET",
        "/@types",
        [
            {"@id": f"{SITE_URL}/@types/Document", "title": "Page", "addable": True},
            {"@id": f"{SITE_URL}/@types/Image", "title": "Image", "addable": False},
        ],
    )
    site.add(
        "GET",
        "/news/@types",
        [
            {"@id": f"{SITE_URL}/@types/Document", "title": "Page", "addable": True},
            {"@id": f"{SITE_URL}/@types/Image", "title": "Image", "addable": False},
        ],
    )
    site.add("GET", "/@types/Document", {"properties": {"title": {}}})
    server = mcp_server.build_server(client)
    assert [t["id"] for t in call(server, "content_types")["items"]] == [
        "Document",
        "Image",
    ]
    addable = call(server, "content_types", addable_in="/news")["items"]
    assert [t["id"] for t in addable] == ["Document"]
    assert call(server, "content_types", portal_type="Document") == {
        "properties": {"title": {}}
    }


def test_block_types_falls_back_to_markdown(client, site):
    site.add("POST", "/@login", {"token": "t"})
    site.add("GET", "/Plone/@blocks-schema", status=404)
    text = call(mcp_server.build_server(client), "block_types")
    assert "(`slate`)" in text


def test_call_service(client, site):
    site.add("GET", "/@registry/plone.site_title", "Site")
    server = mcp_server.build_server(client)
    assert call(
        server, "call_service", method="GET", path="/@registry/plone.site_title"
    ) == {"status": 200, "body": "Site"}


def test_call_service_follows_read_only(client_factory, site):
    server = mcp_server.build_server(client_factory(read_only=True))
    error = tool_error(server, "call_service", method="DELETE", path="/news")
    assert error["error"]["type"] == "PloneReadOnlyError"
    assert site.requests == []


def test_create_content_and_publish(client, site):
    site.add("POST", "/news", {"@id": f"{SITE_URL}/news/hi", "title": "Hi"})
    site.add(
        "GET",
        "/news/hi",
        {"@id": f"{SITE_URL}/news/hi", "review_state": "published", "blocks": {}},
    )
    server = mcp_server.build_server(client)
    result = call(
        server,
        "create_content",
        parent="/news",
        portal_type="News Item",
        data={"title": "Hi"},
        publish="publish",
    )
    assert result == {"@id": f"{SITE_URL}/news/hi", "review_state": "published"}
    assert [r.method for r in site.requests] == ["POST", "POST", "GET"]


def test_create_content_dry_run(client_factory, site):
    server = mcp_server.build_server(client_factory(dry_run=True))
    result = call(
        server,
        "create_content",
        parent="/news",
        portal_type="Document",
        publish="publish",
    )
    assert result["dry_run"] is True
    assert site.requests == []


def test_create_content_takes_a_list_of_blocks(client, site):
    site.add("POST", "/", {"@id": f"{SITE_URL}/hi", "title": "Hi"})
    server = mcp_server.build_server(client)
    call(
        server,
        "create_content",
        parent="/",
        portal_type="Document",
        data={
            "title": "Hi",
            "blocks": [{"@type": "title"}, {"@type": "teaser", "href": "/news"}],
        },
    )
    body = json.loads(site.requests[0].content)
    ids = body["blocks_layout"]["items"]
    assert [body["blocks"][i]["@type"] for i in ids] == ["title", "teaser"]
    assert body["blocks"][ids[1]]["href"] == [{"@id": "/news"}]


def test_update_content_refuses_blocks_without_type(client, site):
    server = mcp_server.build_server(client)
    error = tool_error(server, "update_content", path="/page", data={"blocks": [{}]})
    assert error["error"]["type"] == "ValueError"
    assert site.requests == []


def page_with_blocks():
    return {
        "@id": f"{SITE_URL}/page",
        "title": "Page",
        "blocks": {"t": {"@type": "title"}, "a": {"@type": "slate", "plaintext": "Hi"}},
        "blocks_layout": {"items": ["t", "a"]},
    }


def test_list_blocks(client, site):
    site.add("GET", "/page", page_with_blocks())
    server = mcp_server.build_server(client)
    assert call(server, "list_blocks", path="/page") == {
        "@id": f"{SITE_URL}/page",
        "blocks": [
            {"id": "t", "@type": "title"},
            {"id": "a", "@type": "slate", "text": "Hi"},
        ],
    }


def test_block_tools(client, site):
    site.add("GET", "/page", page_with_blocks())
    server = mcp_server.build_server(client)

    added = call(
        server, "add_blocks", path="/page", items=[{"@type": "image"}], after="t"
    )
    (new,) = added["changed"][0]["added"]
    assert [entry["id"] for entry in added["item"]["blocks"]] == ["t", new, "a"]

    updated = call(
        server, "update_block", path="/page", block_id="a", data={"plaintext": "Yo"}
    )
    assert updated["changed"][0]["updated"] == ["a"]

    removed = call(server, "remove_blocks", path="/page", block_ids=["a"])
    assert removed["item"]["blocks"] == [{"id": "t", "@type": "title"}]

    replaced = call(server, "set_blocks", path="/page", items=[{"@type": "slate"}])
    assert [entry["@type"] for entry in replaced["item"]["blocks"]] == [
        "title",
        "slate",
    ]
    assert [r.method for r in site.requests].count("PATCH") == 4


def test_block_tool_errors_reach_the_model(client, site):
    site.add("GET", "/page", page_with_blocks())
    server = mcp_server.build_server(client)
    error = tool_error(server, "remove_blocks", path="/page", block_ids=["nope"])
    assert error["error"] == {
        "type": "ValueError",
        "message": "No block 'nope' in the item",
    }


def test_update_transition_delete(client, site):
    site.add("PATCH", "/news", {"@id": f"{SITE_URL}/news", "title": "New"})
    site.add("POST", "/news/@workflow/publish", {"review_state": "published"})
    server = mcp_server.build_server(client)
    assert call(server, "update_content", path="/news", data={"title": "New"}) == {
        "@id": f"{SITE_URL}/news",
        "title": "New",
    }
    assert call(server, "run_transition", path="/news", transition="publish") == {
        "review_state": "published"
    }
    assert call(server, "delete_content", paths=["/news", "/events"]) == {
        "deleted": ["/news", "/events"],
        "dry_run": False,
    }


def test_operation_tools(client, site, tmp_path):
    site.add("GET", "/archive", {"is_folderish": True})
    site.add(
        "POST",
        "/archive/@copy",
        [{"source": f"{SITE_URL}/news", "target": f"{SITE_URL}/archive/news"}],
    )
    site.add(
        "POST",
        "/archive/@move",
        [{"source": f"{SITE_URL}/events", "target": f"{SITE_URL}/archive/events"}],
    )
    site.add("GET", "/@types/News Item", {"properties": {}})
    site.add("POST", "/news", {"@id": f"{SITE_URL}/news/x", "title": "X"})
    site.add("GET", "/news/x", {"@id": f"{SITE_URL}/news/x", "title": "X"})
    server = mcp_server.build_server(client)
    assert (
        call(server, "copy_content", sources=["/news"], target="/archive")["operation"]
        == "copy"
    )
    assert (
        call(server, "move_content", sources=["/events"], target="/archive")[
            "operation"
        ]
        == "move"
    )
    result = call(
        server,
        "create_content_with_files",
        parent="/news",
        portal_type="News Item",
        files=[],
        data={"title": "X"},
    )
    assert result["item"]["@id"] == f"{SITE_URL}/news/x"
    (tmp_path / "a.txt").write_text("a")
    site.add("GET", "/docs", {})
    site.add("POST", "/docs", {"@id": f"{SITE_URL}/docs/a.txt"})
    result = call(server, "upload_tree", local_path=str(tmp_path), parent="/docs")
    assert result["created"][0]["@id"] == f"{SITE_URL}/docs/a.txt"


@pytest.mark.skipif(
    not mcp_server.has_html2blocks(),
    reason="collective.html2blocks is not installed",
)
def test_create_page_tool(client, site):
    site.add("POST", "/docs", {"@id": f"{SITE_URL}/docs/hello", "title": "Hello"})
    result = call(
        mcp_server.build_server(client),
        "create_page",
        parent="/docs",
        source="# Hello\n\nText.",
    )
    assert result["item"]["@id"] == f"{SITE_URL}/docs/hello"
    assert site.body()["title"] == "Hello"


@pytest.mark.skipif(
    not mcp_server.has_html2blocks(),
    reason="collective.html2blocks is not installed",
)
def test_create_page_tool_takes_a_type_and_files(client, site, tmp_path):
    photo = tmp_path / "lead.png"
    photo.write_bytes(b"\x89PNG\r\n\x1a\n")
    site.add(
        "GET", "/@types/Post", {"properties": {"blocks": {}, "preview_image_link": {}}}
    )
    site.add("POST", "/docs", {"@id": f"{SITE_URL}/docs/hello", "title": "Hello"})
    site.add(
        "POST", "/docs/hello", {"@id": f"{SITE_URL}/docs/hello/lead.png", "UID": "u1"}
    )
    site.add("PATCH", "/docs/hello", {})
    result = call(
        mcp_server.build_server(client),
        "create_page",
        parent="/docs",
        source="# Hello\n\nText.",
        portal_type="Post",
        files=[str(photo)],
    )
    assert result["item"]["@id"] == f"{SITE_URL}/docs/hello"
    assert site.body(site.requests[1])["@type"] == "Post"
    assert site.body(site.requests[3]) == {"preview_image_link": "u1"}
    assert result["changed"][0]["fields"] == {
        "preview_image_link": f"{SITE_URL}/docs/hello/lead.png"
    }


@pytest.mark.skipif(
    not mcp_server.has_html2blocks(),
    reason="collective.html2blocks is not installed",
)
def test_create_page_tool_describes_the_type(client):
    schema = tools(mcp_server.build_server(client))["create_page"].input_schema
    assert "blocks" in schema["properties"]["portal_type"]["description"]
    assert "files" in schema["properties"]
    assert "lead_image" in schema["properties"]


def test_site_info(client, site):
    site.add("GET", "/@actions", {"user": [{"id": "logout"}]})
    site.add("GET", "/@system", {"plone_version": "6.1.3"})
    info = call(mcp_server.build_server(client), "site_info")
    assert info["authenticated"] is True
    assert info["plone_version"] == "6.1.3"
    assert info["frontend_url"] == SITE_URL
    assert info["dry_run"] is False


def test_get_navigation(client, site):
    site.add("GET", "/@navigation", {"items": []})
    assert call(mcp_server.build_server(client), "get_navigation", depth=3) == {
        "items": []
    }
    assert ("expand.navigation.depth", "3") in site.params()


OTHER_URL = "http://other.test/Plone"


@pytest.fixture
def sites(site):
    """Build the sites of two anonymous profiles, recording each client made."""
    made = []

    def build(read_only=False, dry_run=False, docs_read_only=False):
        def factory(**settings):
            made.append(settings["url"])
            return PloneClient(**{
                **settings,
                "transport": site.transport,
                "retries": 0,
            })

        profiles = [
            Profile(name="blog", url=SITE_URL, description="The blog"),
            Profile(name="docs", url=OTHER_URL, read_only=docs_read_only),
        ]
        return mcp_server.Sites.from_profiles(
            profiles, read_only=read_only, dry_run=dry_run, factory=factory
        )

    build.made = made
    return build


def test_one_site_has_no_site_argument(client):
    found = tools(mcp_server.build_server(client))
    assert "list_sites" not in found
    assert "site" not in found["get_content"].input_schema["properties"]


def test_several_sites_take_a_site_argument(sites):
    server = mcp_server.build_server(sites())
    found = tools(server)
    assert set(found) == READ_TOOLS | WRITE_TOOLS | {"list_sites"}
    for name, tool in found.items():
        if name == "list_sites":
            continue
        schema = tool.input_schema
        assert schema["properties"]["site"]["enum"] == ["blog", "docs"], name
        assert "site" in schema["required"], name
        assert "client" not in schema["properties"], name
    assert "- `blog`, http://plone.test/Plone: The blog" in server.instructions
    assert server.title == "Plone sites blog, docs"


def test_list_sites(sites):
    server = mcp_server.build_server(sites())
    assert call(server, "list_sites")["items"] == [
        {
            "name": "blog",
            "url": SITE_URL,
            "description": "The blog",
            "read_only": False,
        },
        {"name": "docs", "url": OTHER_URL, "description": "", "read_only": False},
    ]


def test_tools_go_to_the_site_asked_for(sites, site):
    built = sites()
    server = mcp_server.build_server(built)
    assert sites.made == []
    site.add("GET", "/news", {"title": "News"})
    call(server, "get_content", site="docs", path="/news")
    assert site.last.url.host == "other.test"
    assert sites.made == [OTHER_URL]
    call(server, "get_content", site="blog", path="/news")
    call(server, "get_content", site="docs", path="/news")
    assert site.last.url.host == "other.test"
    assert sites.made == [OTHER_URL, SITE_URL]
    built.close()
    assert built.client("docs") is not None
    assert sites.made == [OTHER_URL, SITE_URL, OTHER_URL]


def test_unknown_site_is_refused(sites):
    with pytest.raises(ToolError):
        asyncio.run(
            mcp_server.build_server(sites()).call_tool(
                "get_content", {"site": "nope", "path": "/"}
            )
        )
    with pytest.raises(PloneConfigurationError, match="Unknown site 'nope'"):
        sites().client("nope")


def test_read_only_site_refuses_changes(sites, site):
    built = sites(docs_read_only=True)
    server = mcp_server.build_server(built)
    assert set(tools(server)) >= WRITE_TOOLS
    assert "`docs`, http://other.test/Plone (read-only)" in server.instructions
    error = tool_error(server, "delete_content", site="docs", paths=["/news"])
    assert error["error"]["type"] == "PloneReadOnlyError"
    assert site.requests == []
    call(server, "delete_content", site="blog", paths=["/news"])
    assert site.last.url.host == "plone.test"


def test_read_only_flag_covers_every_site(sites):
    built = sites(read_only=True)
    assert [s.read_only for s in built] == [True, True]
    assert set(tools(mcp_server.build_server(built))) == READ_TOOLS | {"list_sites"}


def test_dry_run_covers_every_site(sites, site):
    server = mcp_server.build_server(sites(dry_run=True))
    assert "This server is in a dry run." in server.instructions
    result = call(server, "delete_content", site="docs", paths=["/news"])
    assert result["dry_run"] is True
    assert site.requests == []


def test_sites_validation(client):
    with pytest.raises(ValueError, match="at least one site"):
        mcp_server.Sites([])
    site = mcp_server.Site("a", SITE_URL, client=client)
    with pytest.raises(ValueError, match="'a' is given twice"):
        mcp_server.Sites([site, site])


def test_serve_closes_the_clients(sites, monkeypatch):
    built = sites()
    built.client("blog")
    monkeypatch.setattr(mcp_server.MCPServer, "run", lambda self, transport: None)
    mcp_server.serve(built)
    assert all(s.client is None for s in built)


def test_site_info_reports_rejected_credentials(client, site):
    site.add("GET", "/@actions", {"user": [{"id": "login"}]})
    info = call(mcp_server.build_server(client), "site_info")
    assert info["authenticated"] is False
    assert info["credentials_rejected"] is True


def test_site_info_anonymous_client_is_not_rejected(client_factory, site):
    site.add("GET", "/@actions", {"user": [{"id": "login"}]})
    anonymous = client_factory(username="", password="")
    info = call(mcp_server.build_server(anonymous), "site_info")
    assert info["credentials_rejected"] is False


def test_instructions_warn_about_rejected_credentials(client):
    server = mcp_server.build_server(client, rejected=("blog",))
    assert "credentials of `blog` were rejected" in server.instructions
    assert "plone-client profile set-secret blog" in server.instructions
    assert "were rejected" not in mcp_server.build_server(client).instructions


def test_rejected_sites_names_only_the_rejected(client_factory, site):
    site.add("GET", "/@actions", {"user": [{"id": "login"}]})
    sites = mcp_server.Sites([
        mcp_server.Site("blog", SITE_URL, client=client_factory()),
        mcp_server.Site(
            "docs", SITE_URL, client=client_factory(username="", password="")
        ),
    ])
    assert mcp_server.rejected_sites(sites) == ["blog"]


def test_serve_warns_on_stderr_and_still_starts(
    client_factory, site, monkeypatch, capsys
):
    site.add("GET", "/@actions", {"user": [{"id": "login"}]})
    built, started = [], []

    class FakeServer:
        def run(self, transport: str) -> None:
            started.append(transport)

    def fake_build(target, rejected=()):
        built.append(rejected)
        return FakeServer()

    monkeypatch.setattr(mcp_server, "build_server", fake_build)
    mcp_server.serve(client_factory())
    err = capsys.readouterr().err
    assert "plone-client: warning: Credentials were rejected" in err
    assert "profile set-secret site" in err
    assert built == [("site",)]
    assert started == ["stdio"]


def test_serve_is_quiet_without_credentials(client_factory, site, monkeypatch, capsys):
    site.add("GET", "/@actions", {"user": [{"id": "login"}]})
    built = []

    class FakeServer:
        def run(self, transport: str) -> None:
            pass

    def fake_build(target, rejected=()):
        built.append(rejected)
        return FakeServer()

    monkeypatch.setattr(mcp_server, "build_server", fake_build)
    mcp_server.serve(client_factory(username="", password=""))
    assert capsys.readouterr().err == ""
    assert built == [()]
