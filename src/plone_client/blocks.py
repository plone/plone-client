"""Helpers for Volto blocks: build them, walk them, find their links.

A page built with Volto stores its content in two fields: ``blocks``, a
mapping of block ids to block data, and ``blocks_layout``, whose ``items``
list the block ids in order. A page without both renders empty.

Example::

    from plone_client import blocks

    page = blocks.build(
        blocks.title(),
        blocks.description(),
        blocks.text("Hello!"),
    )
    site.content.create("/", "Document", title="Hello", **page)
"""

from collections.abc import Iterator
from collections.abc import Mapping
from typing import Any

import uuid


#: Keys whose string values are links.
LINK_KEYS = frozenset({"url", "href", "link", "preview_image_link"})


def new_id() -> str:
    """A fresh block id.

    :returns: A random UUID, the way Volto writes block ids.
    """
    return str(uuid.uuid4())


def build(*items: Mapping[str, Any]) -> dict[str, Any]:
    """``blocks`` and ``blocks_layout`` for blocks in order.

    :param items: Block data, each with an ``@type``.
    :returns: A mapping with ``blocks`` and ``blocks_layout``, ready to merge
        into the data of an item.
    """
    ids = [new_id() for _ in items]
    return {
        "blocks": {
            block_id: dict(item) for block_id, item in zip(ids, items, strict=True)
        },
        "blocks_layout": {"items": ids},
    }


def title() -> dict[str, Any]:
    """A title block, which shows the item's title.

    :returns: The block.
    """
    return {"@type": "title"}


def description() -> dict[str, Any]:
    """A description block, which shows the item's description.

    :returns: The block.
    """
    return {"@type": "description"}


def text(value: str) -> dict[str, Any]:
    """A text block with one plain paragraph.

    :param value: The text.
    :returns: A ``slate`` block.
    """
    return {
        "@type": "slate",
        "value": [{"type": "p", "children": [{"text": value}]}],
        "plaintext": value,
    }


def iter_blocks(
    blocks: Mapping[str, Any] | None,
    layout: Mapping[str, Any] | None = None,
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Every block, nested ones included, depth first.

    Blocks are visited in layout order. Container blocks (grids, columns,
    accordions…) keep their children either in their own ``blocks`` and
    ``blocks_layout`` or inside ``data``; both are followed. Blocks missing
    from the layout come last.

    :param blocks: The ``blocks`` of an item or of a container block.
    :param layout: The matching ``blocks_layout``.
    :returns: Pairs of block id and block data.
    """
    blocks = blocks or {}
    order = list((layout or {}).get("items") or [])
    order += [block_id for block_id in blocks if block_id not in order]
    for block_id in order:
        block = blocks.get(block_id)
        if not isinstance(block, dict):
            continue
        yield block_id, block
        for holder in (block, block.get("data")):
            if isinstance(holder, dict) and isinstance(holder.get("blocks"), dict):
                yield from iter_blocks(holder["blocks"], holder.get("blocks_layout"))


def iter_links(node: Any) -> Iterator[str]:
    """Every link inside a block, or inside any value.

    Finds string values of ``url``, ``href``, ``link`` and
    ``preview_image_link`` keys, and the ``@id`` of the objects that object
    browser widgets store in lists (``"href": [{"@id": …}]``).

    :param node: A block, a mapping of blocks, or any JSON value.
    :returns: Each link, in document order.
    """
    if isinstance(node, Mapping):
        for key, value in node.items():
            if key in LINK_KEYS and isinstance(value, str):
                yield value
            elif key in LINK_KEYS and isinstance(value, list):
                for entry in value:
                    if isinstance(entry, Mapping) and isinstance(entry.get("@id"), str):
                        yield entry["@id"]
                    else:
                        yield from iter_links(entry)
            else:
                yield from iter_links(value)
    elif isinstance(node, list):
        for value in node:
            yield from iter_links(value)
