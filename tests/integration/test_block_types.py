"""plone-client against the ``@blocks-schema`` service of a real Volto server."""

from . import PASSWORD
from . import USERNAME
from collections.abc import Generator
from plone_client import PloneClient
from plone_client.exceptions import PloneNotFoundError

import asyncio
import json
import pytest


pytestmark = pytest.mark.integration


@pytest.fixture(params=["basic", "jwt"])
def volto(request, plone_url, volto_url) -> Generator[PloneClient]:
    """A client of the backend that knows the Volto server."""
    with PloneClient(
        plone_url,
        username=USERNAME,
        password=PASSWORD,
        auth_method=request.param,
        frontend_url=volto_url,
    ) as client:
        yield client


def test_list(volto):
    result = volto.block_types.list()
    assert result["source"] == "site"
    assert "teaser" in {item["id"] for item in result["items"]}


def test_get(volto):
    result = volto.block_types.get("teaser")
    assert result["source"] == "site"
    assert "href" in result["schema"]["properties"]


def test_markdown(volto):
    assert "(`teaser`)" in volto.block_types.markdown("teaser")


def test_unknown_block(volto):
    with pytest.raises(PloneNotFoundError):
        volto.block_types.get("not-a-block")


def test_blocks_for_an_item(volto):
    item = volto.content.create("/", "Document", title="Blocks")
    path = volto.path(item["@id"])
    try:
        ids = {entry["id"] for entry in volto.block_types.list(path)["items"]}
    finally:
        volto.content.delete(path)
    assert "teaser" in ids
    assert "detachedSlate" not in ids


def test_mcp_resources(volto):
    mcp_server = pytest.importorskip("plone_client.mcp_server")
    server = mcp_server.build_server(volto)
    item = volto.content.create("/", "Document", title="Resource")
    path = volto.path(item["@id"]).lstrip("/")

    def read(uri: str) -> str:
        (content,) = asyncio.run(server.read_resource(uri))
        return content.content

    try:
        assert json.loads(read(f"plone://site/content/{path}"))["title"] == "Resource"
    finally:
        volto.content.delete(f"/{path}")
    assert json.loads(read("plone://site/site"))["@type"] == "Plone Site"
    titles = {entry["title"] for entry in json.loads(read("plone://site/types"))}
    assert "Page" in titles
    assert "properties" in json.loads(read("plone://site/types/Document"))
    assert "(`teaser`)" in read("plone://site/blocks")
    assert "(`teaser`)" in read("plone://site/blocks/teaser")


def test_an_expired_token_is_renewed(volto):
    assert volto.block_types.list()["source"] == "site"
    volto._token = "expired"
    if volto._http.auth is not None and hasattr(volto._http.auth, "token"):
        volto._http.auth.token = "expired"
    assert volto.block_types.list()["source"] == "site"
