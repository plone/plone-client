from . import SITE_URL
from mcp import Client
from mcp.server.mcpserver.exceptions import ResourceError
from mcp.server.mcpserver.exceptions import ResourceNotFoundError
from mcp.shared.exceptions import MCPError
from plone_client import mcp_server

import asyncio
import httpx
import json
import pytest
import threading


STATIC = {"plone://site/site", "plone://site/types", "plone://site/blocks"}
TEMPLATES = {
    "plone://site/content/{+path}",
    "plone://site/types/{portal_type}",
    "plone://site/blocks/{block_id}",
}


def resources(server):
    return {str(r.uri): r for r in asyncio.run(server.list_resources())}


def templates(server):
    return {t.uri_template: t for t in asyncio.run(server.list_resource_templates())}


def read(server, uri):
    """Read a resource, and return its only content."""
    (content,) = asyncio.run(server.read_resource(uri))
    return content


def read_json(server, uri):
    content = read(server, uri)
    assert content.mime_type == "application/json"
    return json.loads(content.content)


def add_markdown(site, path, text):
    site.add("POST", "/@login", {"token": "t"})
    site.add_callable(
        "GET",
        path,
        lambda request: httpx.Response(
            200, text=text, headers={"Content-Type": "text/markdown"}
        ),
    )


def test_resources_of_one_site(client):
    server = mcp_server.build_server(client)
    assert set(resources(server)) == STATIC
    assert set(templates(server)) == TEMPLATES
    assert all(item.description for item in resources(server).values())
    assert all(item.description for item in templates(server).values())


def test_site_root(client, site):
    site.add("GET", "/", {"@id": SITE_URL, "title": "Site"})
    server = mcp_server.build_server(client)
    assert read_json(server, "plone://site/site")["title"] == "Site"


def test_content_item(client, site):
    site.add("GET", "/news/item", {"@id": f"{SITE_URL}/news/item"})
    server = mcp_server.build_server(client)
    result = read_json(server, "plone://site/content/news/item")
    assert result["@id"] == f"{SITE_URL}/news/item"


def test_types(client, site):
    site.add("GET", "/@types", [{"title": "Page"}])
    site.add("GET", "/@types/Document", {"title": "Page", "properties": {}})
    server = mcp_server.build_server(client)
    assert read_json(server, "plone://site/types") == [{"title": "Page"}]
    assert read_json(server, "plone://site/types/Document")["title"] == "Page"


def test_blocks(client, site):
    add_markdown(site, "/Plone/@blocks-schema", "# Blocks")
    add_markdown(site, "/Plone/@blocks-schema/teaser", "## Teaser")
    server = mcp_server.build_server(client)
    listing = read(server, "plone://site/blocks")
    assert listing.mime_type == "text/markdown"
    assert listing.content == "# Blocks"
    assert read(server, "plone://site/blocks/teaser").content == "## Teaser"


def test_blocks_fall_back_to_the_core_blocks(client, site):
    site.add("POST", "/@login", {"token": "t"})
    site.add("GET", "/Plone/@blocks-schema", status=404)
    server = mcp_server.build_server(client)
    assert "(`teaser`)" in read(server, "plone://site/blocks").content


def several_sites(client_factory):
    return mcp_server.Sites([
        mcp_server.Site("blog", SITE_URL, client=client_factory()),
        mcp_server.Site("My Docs", SITE_URL, client=client_factory()),
    ])


def test_each_site_has_its_own_uris(client_factory, site):
    server = mcp_server.build_server(several_sites(client_factory))
    found = set(resources(server))
    assert {"plone://blog/site", "plone://My%20Docs/site"} <= found
    assert len(found) == 2 * len(STATIC)
    assert "plone://blog/content/{+path}" in templates(server)
    assert "plone://My%20Docs/content/{+path}" in templates(server)
    site.add("GET", "/news", {"title": "News"})
    assert read_json(server, "plone://My%20Docs/content/news")["title"] == "News"


def test_unknown_site(client):
    server = mcp_server.build_server(client)
    with pytest.raises(ResourceNotFoundError):
        read(server, "plone://other/site")


@pytest.mark.parametrize(
    "tool,static,dynamic",
    [
        ("get_content", {"plone://site/site"}, {"plone://site/content/{+path}"}),
        ("content_types", {"plone://site/types"}, {"plone://site/types/{portal_type}"}),
        ("block_types", {"plone://site/blocks"}, {"plone://site/blocks/{block_id}"}),
        ("search", set(), set()),
    ],
)
def test_tool_choice_limits_the_resources(client, tool, static, dynamic):
    server = mcp_server.build_server(client, tools=[tool])
    assert set(resources(server)) == static
    assert set(templates(server)) == dynamic


def test_missing_item_is_not_found(client, site):
    site.add("GET", "/missing", {"message": "gone"}, status=404)
    server = mcp_server.build_server(client)
    with pytest.raises(ResourceNotFoundError, match="gone"):
        read(server, "plone://site/content/missing")


def test_refused_item_keeps_its_message(client, site):
    site.add("GET", "/secret", {"message": "no access"}, status=403)
    server = mcp_server.build_server(client)
    with pytest.raises(ResourceError, match="no access") as info:
        read(server, "plone://site/content/secret")
    assert not isinstance(info.value, ResourceNotFoundError)


def test_clients_get_the_not_found_code(client, site):
    site.add("GET", "/missing", {"message": "gone"}, status=404)
    server = mcp_server.build_server(client)

    async def main():
        async with Client(server) as connected:
            with pytest.raises(MCPError) as info:
                await connected.read_resource("plone://site/content/missing")
        return info.value.error.code

    assert asyncio.run(main()) == -32602


@pytest.mark.parametrize(
    "uri",
    [
        "plone://site/content/../@users",
        "plone://site/content/news/%2E%2E/%2E%2E/@users",
    ],
)
def test_paths_cannot_leave_the_content(client, site, uri):
    server = mcp_server.build_server(client)
    with pytest.raises(ResourceError):
        read(server, uri)
    assert site.requests == []


def test_resources_wait_for_the_site_lock(client, site):
    site.add("GET", "/news", {"title": "News"})
    sites = mcp_server.Sites.from_client(client)
    server = mcp_server.build_server(sites)
    done = threading.Event()

    def reader():
        read(server, "plone://site/content/news")
        done.set()

    lock = next(iter(sites)).lock
    with lock:
        thread = threading.Thread(target=reader)
        thread.start()
        assert not done.wait(0.1)
    thread.join(5)
    assert done.is_set()
