from .. import SITE_URL
from plone_client.exceptions import PloneAuthenticationError
from plone_client.exceptions import PloneNotFoundError
from plone_client.managers.block_types import CORE_BLOCKS
from plone_client.managers.block_types import core_docs

import httpx
import pytest


#: Site path of the service on the fake site: the frontend URL is the site URL.
SERVICE = "/Plone/@blocks-schema"

LISTING = {
    "@id": f"{SITE_URL}/@blocks-schema",
    "items": [{"@id": f"{SITE_URL}/@blocks-schema/slate", "id": "slate"}],
    "items_total": 1,
}


@pytest.fixture
def token_site(site):
    """The fake site, answering @login with a token."""
    site.add("POST", "/@login", {"token": "jwt-token"})
    return site


def test_list_from_the_site(client, token_site):
    token_site.add("GET", SERVICE, LISTING)
    result = client.block_types.list()
    assert result == {**LISTING, "source": "site"}
    login, request = token_site.requests
    assert token_site.body(login) == {"login": "admin", "password": "secret"}
    assert str(request.url) == f"{SITE_URL}/@blocks-schema"
    assert request.headers["Authorization"] == "Bearer jwt-token"
    assert request.headers["Accept"] == "application/json"


def test_the_token_is_asked_for_once(client, token_site):
    token_site.add("GET", SERVICE, LISTING)
    client.block_types.list()
    client.block_types.list()
    methods = [request.method for request in token_site.requests]
    assert methods == ["POST", "GET", "GET"]


def test_a_given_token_is_sent(client_factory, site):
    site.add("GET", SERVICE, LISTING)
    with client_factory(username="", password="", token="given") as client:
        client.block_types.list()
    assert [r.method for r in site.requests] == ["GET"]
    assert site.last.headers["Authorization"] == "Bearer given"


def test_get_one_block_for_an_item(client, token_site):
    token_site.add("GET", "/Plone/news/@blocks-schema/teaser", {"id": "teaser"})
    result = client.block_types.get("teaser", "/news")
    assert result == {"id": "teaser", "source": "site"}
    assert str(token_site.last.url) == f"{SITE_URL}/news/@blocks-schema/teaser"


def test_frontend_url(client_factory, site):
    site.add("POST", "/@login", {"token": "t"})
    site.add_callable(
        "GET",
        "/@blocks-schema",
        lambda request: httpx.Response(200, json=LISTING),
    )
    with client_factory(frontend_url="http://www.plone.test/") as client:
        assert client.block_types.list()["source"] == "site"
    assert str(site.last.url) == "http://www.plone.test/@blocks-schema"


def test_markdown(client, token_site):
    token_site.add_callable(
        "GET",
        SERVICE,
        lambda request: httpx.Response(
            200, text="# Blocks", headers={"Content-Type": "text/markdown"}
        ),
    )
    assert client.block_types.markdown() == "# Blocks"
    assert token_site.last.headers["Accept"] == "text/markdown"


def _html(request: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200, text="<html></html>", headers={"Content-Type": "text/html"}
    )


@pytest.mark.parametrize(
    "setup,reason",
    [
        # an older Volto renders its page for any path
        (
            lambda site: site.add_callable("GET", SERVICE, _html),
            "has no @blocks-schema",
        ),
        # the backend has no such service
        (lambda site: site.add("GET", SERVICE, status=404), "has no @blocks-schema"),
    ],
)
def test_list_falls_back_to_the_core_blocks(client, token_site, setup, reason):
    setup(token_site)
    result = client.block_types.list()
    assert result["source"] == "builtin"
    assert reason in result["warning"]
    assert [entry["id"] for entry in result["items"]] == list(CORE_BLOCKS)
    slate = result["items"][0]
    assert slate["title"] == "Text"
    assert slate["description"].startswith("Holds rich text")
    assert "restricted" not in slate
    title = next(entry for entry in result["items"] if entry["id"] == "title")
    assert title["restricted"] == "context"


def test_anonymous_clients_fall_back(client_factory, site):
    site.add("GET", SERVICE, status=401)
    with client_factory(username="", password="") as client:
        result = client.block_types.list()
    assert result["source"] == "builtin"
    assert "authenticated user" in result["warning"]
    assert "Authorization" not in site.last.headers


def test_unreachable_frontend_falls_back(client_factory, site):
    site.add("POST", "/@login", {"token": "t"})

    def refuse(request):
        raise httpx.ConnectError("refused", request=request)

    site.add_callable("GET", "/@blocks-schema", refuse)
    with client_factory(frontend_url="http://www.plone.test") as client:
        result = client.block_types.list()
    assert result["source"] == "builtin"
    assert "cannot be reached" in result["warning"]


def test_refused_token_raises(client, token_site):
    token_site.add("GET", SERVICE, {"message": "Invalid token"}, status=401)
    with pytest.raises(PloneAuthenticationError):
        client.block_types.list()


def test_get_falls_back_to_a_core_block(client, token_site):
    token_site.add_callable("GET", f"{SERVICE}/teaser", _html)
    result = client.block_types.get("teaser")
    assert result["source"] == "builtin"
    assert result["schema"] is None
    assert result["docs"].startswith("Shows a card that links to one content item")


def test_get_unknown_core_block(client, token_site):
    token_site.add_callable("GET", f"{SERVICE}/fancy", _html)
    with pytest.raises(PloneNotFoundError, match="not one of Volto's core blocks"):
        client.block_types.get("fancy")


def test_get_unknown_block_of_the_site(client, token_site):
    token_site.add("GET", f"{SERVICE}/fancy", {"message": "Not found"}, status=404)
    token_site.add("GET", SERVICE, LISTING)
    with pytest.raises(PloneNotFoundError):
        client.block_types.get("fancy")


def test_get_missing_service_falls_back(client, token_site):
    token_site.add("GET", f"{SERVICE}/slate", status=404)
    token_site.add("GET", SERVICE, status=404)
    assert client.block_types.get("slate")["source"] == "builtin"


def test_markdown_falls_back(client, token_site):
    token_site.add("GET", SERVICE, status=404)
    text = client.block_types.markdown()
    assert text.startswith("> ")
    assert "- **Text** (`slate`): Holds rich text" in text
    block = client.block_types.markdown("toc")
    assert "# Table of Contents (`toc`)" in block


def test_core_docs_fill_placeholders():
    docs = core_docs("gridBlock")
    assert "{{" not in docs
    assert "up to 4 blocks" in docs
    assert not docs.startswith("---")


@pytest.mark.parametrize("block_id", list(CORE_BLOCKS))
def test_every_core_block_has_docs(block_id):
    assert core_docs(block_id)
