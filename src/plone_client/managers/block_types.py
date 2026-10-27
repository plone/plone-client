"""Block types: the blocks a Volto site offers, with their docs and schemas.

The list of blocks only exists in the frontend, so it comes from the
``@blocks-schema`` service of the Volto server, not from ``plone.restapi``.
Sites whose Volto does not have that service yet, clients that talk to the
backend directly, and anonymous clients get the documentation of Volto's
core blocks that ships with plone-client instead, marked with
``"source": "builtin"`` and a ``warning`` that says why.
"""

from ..exceptions import error_from_response
from ..exceptions import PloneAPIError
from ..exceptions import PloneConnectionError
from ..exceptions import PloneNotFoundError
from .base import BaseManager
from functools import cache
from importlib.resources import files
from typing import Any

import httpx
import re


SERVICE = "@blocks-schema"
JSON = "application/json"
MARKDOWN = "text/markdown"

#: Title and ``restricted`` of Volto's core blocks, from its configuration.
#: ``"context"`` means the block chooser decides per content item.
CORE_BLOCKS: dict[str, tuple[str, bool | str]] = {
    "slate": ("Text", False),
    "title": ("Title", "context"),
    "description": ("Description", False),
    "image": ("Image", False),
    "teaser": ("Teaser", False),
    "listing": ("Listing", False),
    "gridBlock": ("Grid", False),
    "search": ("Search", False),
    "video": ("Video", False),
    "maps": ("Maps", False),
    "html": ("HTML", False),
    "toc": ("Table of Contents", False),
    "detachedSlate": ("Detached Slate", True),
}

#: Values of the placeholders in the core docs, from Volto's configuration.
PLACEHOLDERS: dict[str, dict[str, str]] = {
    "gridBlock": {
        "maxLength": "4",
        "allowedBlocks": "`image`, `listing`, `slate` and `teaser`",
    },
}

FRONTMATTER_RE = re.compile(r"\A---\n(?P<meta>.*?)\n---\n", re.DOTALL)
PLACEHOLDER_RE = re.compile(r"\{\{\s*(\w+)\s*\}\}")


class BlocksSchemaUnavailable(Exception):
    """The site has no ``@blocks-schema`` service that the client can use.

    :param reason: Why, for the ``warning`` of the builtin answer.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@cache
def core_docs(block_id: str) -> str:
    """Documentation of a core block, as shipped with plone-client.

    :param block_id: Block id, such as ``slate``.
    :returns: The Markdown, without its frontmatter and with its
        placeholders filled in.
    :raises KeyError: If the block is not a core block.
    """
    if block_id not in CORE_BLOCKS:
        raise KeyError(block_id)
    text = files("plone_client").joinpath("block_docs", f"{block_id}.md").read_text()
    text = FRONTMATTER_RE.sub("", text).strip()
    values = PLACEHOLDERS.get(block_id, {})
    return PLACEHOLDER_RE.sub(lambda match: values.get(match[1], match[0]), text)


def summary(docs: str) -> str:
    """First paragraph of a block's documentation.

    :param docs: The Markdown.
    :returns: The paragraph, on one line.
    """
    return " ".join(docs.strip().split("\n\n", 1)[0].split())


def builtin_list(reason: str) -> dict[str, Any]:
    """The core blocks, in the shape of ``GET @blocks-schema``.

    :param reason: Why the site's own list is not used.
    :returns: ``items``, ``items_total``, ``source`` and ``warning``.
    """
    items = []
    for block_id, (title, restricted) in CORE_BLOCKS.items():
        entry: dict[str, Any] = {
            "id": block_id,
            "title": title,
            "description": summary(core_docs(block_id)),
        }
        if restricted:
            entry["restricted"] = restricted
        items.append(entry)
    return {
        "items": items,
        "items_total": len(items),
        "source": "builtin",
        "warning": reason,
    }


def builtin_block(block_id: str, reason: str) -> dict[str, Any]:
    """One core block, in the shape of ``GET @blocks-schema/<id>``.

    :param block_id: Block id.
    :param reason: Why the site's own description is not used.
    :returns: ``id``, ``title``, ``docs`` (no ``schema``: only the site knows
        it), ``source`` and ``warning``.
    :raises KeyError: If the block is not a core block.
    """
    title, _ = CORE_BLOCKS[block_id]
    return {
        "id": block_id,
        "title": title,
        "docs": core_docs(block_id),
        "schema": None,
        "variations": [],
        "source": "builtin",
        "warning": reason,
    }


def builtin_markdown(data: dict[str, Any]) -> str:
    """Markdown for a builtin answer, like the service's ``text/markdown``.

    :param data: A builtin list or block.
    :returns: The Markdown.
    """
    if "items" in data:
        lines = [
            f"- **{entry['title']}** (`{entry['id']}`): {entry['description']}"
            for entry in data["items"]
        ]
        return "\n".join(["# Blocks", "", *lines, ""])
    return f"# {data['title']} (`{data['id']}`)\n\n{data['docs']}\n"


class BlockTypesManager(BaseManager):
    """The blocks a Volto site offers (``@blocks-schema`` of the Volto server).

    Requests go to the client's ``frontend_url`` with a Bearer token, which
    the client gets from ``@login`` when it uses basic authentication.
    """

    def _path(self, ref: str | None, block_id: str | None) -> str:
        """Path of the service, for a content item and a block.

        :param ref: Content item whose block chooser to ask, if any.
        :param block_id: Block id, if any.
        :returns: The site path.
        """
        base = self._resolve(ref).rstrip("/") if ref else ""
        return f"{base}/{SERVICE}" + (f"/{block_id}" if block_id else "")

    def _fetch(self, path: str, accept: str) -> httpx.Response:
        """Ask the Volto server, telling a missing service from an error.

        :param path: Site path of the service.
        :param accept: Media type to ask for.
        :returns: A successful answer of the service.
        :raises BlocksSchemaUnavailable: If the service is not there, or
            the client cannot use it.
        :raises PloneNotFoundError: If the service is there but the block or
            the content item is not.
        :raises PloneAPIError: For any other error of the service.
        """
        client = self._client
        try:
            response = client.frontend_request(
                "GET", path, headers={"Accept": accept}, raise_for_status=False
            )
        except PloneConnectionError as error:
            raise BlocksSchemaUnavailable(
                f"{client.frontend_url} cannot be reached: {error}"
            ) from error
        except PloneAPIError as error:
            # the client could not get a token
            raise BlocksSchemaUnavailable(f"no token for {SERVICE}: {error}") from error
        content_type = response.headers.get("Content-Type", "")
        status = response.status_code
        if status == 200 and content_type.startswith(accept):
            return response
        if status == 200:
            raise BlocksSchemaUnavailable(
                f"{client.frontend_url} has no {SERVICE} service (it answered "
                f"{content_type or 'without a content type'}); set frontend_url "
                "to the Volto server, or upgrade Volto"
            )
        if status == 401 and not client.token():
            raise BlocksSchemaUnavailable(f"{SERVICE} needs an authenticated user")
        if status == 404 and SERVICE in path and self._service_missing():
            raise BlocksSchemaUnavailable(
                f"{client.frontend_url} has no {SERVICE} service; set "
                "frontend_url to the Volto server, or upgrade Volto"
            )
        raise error_from_response(response)

    def _service_missing(self) -> bool:
        """Say whether a ``404`` came from a missing service.

        :returns: ``True`` if the root of the service is not found either.
        """
        response = self._client.frontend_request(
            "GET", f"/{SERVICE}", raise_for_status=False
        )
        return response.status_code == 404 or not response.headers.get(
            "Content-Type", ""
        ).startswith(JSON)

    def list(self, ref: str | None = None) -> dict[str, Any]:
        """The blocks of the site, with their title and summary.

        :param ref: A content item; only the blocks that editors can add to
            it are listed (their ``restricted`` is evaluated for it).
        :returns: ``items`` (``id``, ``title``, ``description``, maybe
            ``restricted``), ``items_total`` and ``source``: ``site``, or
            ``builtin`` with a ``warning`` when the site cannot tell.
        """
        try:
            response = self._fetch(self._path(ref, None), JSON)
        except BlocksSchemaUnavailable as error:
            return builtin_list(error.reason)
        return {**response.json(), "source": "site"}

    def get(self, block_id: str, ref: str | None = None) -> dict[str, Any]:
        """One block: its documentation, data schema and variations.

        :param block_id: Block id, such as ``teaser``.
        :param ref: A content item; ``restricted`` is evaluated for it.
        :returns: ``id``, ``title``, ``docs``, ``schema``, ``variations`` and
            ``source``; builtin answers have no schema.
        :raises PloneNotFoundError: If there is no such block.
        """
        try:
            response = self._fetch(self._path(ref, block_id), JSON)
        except BlocksSchemaUnavailable as error:
            return self._builtin_block(block_id, error.reason)
        return {**response.json(), "source": "site"}

    def markdown(self, block_id: str | None = None, ref: str | None = None) -> str:
        """The list of blocks, or one block, as Markdown.

        Easier for a language model to read than the JSON schema.

        :param block_id: Block id; without it, the list.
        :param ref: A content item, as in :meth:`list`.
        :returns: The Markdown.
        :raises PloneNotFoundError: If there is no such block.
        """
        try:
            response = self._fetch(self._path(ref, block_id), MARKDOWN)
        except BlocksSchemaUnavailable as error:
            data = (
                self._builtin_block(block_id, error.reason)
                if block_id
                else builtin_list(error.reason)
            )
            return f"> {data['warning']}\n\n{builtin_markdown(data)}"
        return response.text

    def _builtin_block(self, block_id: str, reason: str) -> dict[str, Any]:
        """A core block, or a not found error.

        :param block_id: Block id.
        :param reason: Why the site's own description is not used.
        :returns: The block.
        :raises PloneNotFoundError: If it is not a core block.
        """
        try:
            return builtin_block(block_id, reason)
        except KeyError:
            raise PloneNotFoundError(
                f"{block_id!r} is not one of Volto's core blocks, and the site "
                f"cannot list its own ({reason})",
                status_code=404,
                error_type="NotFound",
                method="GET",
                url=f"{self._client.frontend_url}/{SERVICE}/{block_id}",
            ) from None
