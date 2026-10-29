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

Blocks this module has no helper for, such as those of an add-on, are built
with :func:`block`, and blocks that hold other blocks with :func:`container`.
A grid of four teasers::

    paths = ["/news/a", "/news/b", "/news/c", "/news/d"]
    page = blocks.build(
        blocks.title(),
        blocks.grid(*(blocks.teaser(path) for path in paths)),
    )

Markdown and HTML can be converted to blocks with :func:`convert`.
"""

from .exceptions import PloneConfigurationError
from collections.abc import Iterable
from collections.abc import Iterator
from collections.abc import Mapping
from typing import Any
from typing import Literal

import html
import uuid


SourceFormat = Literal["markdown", "html"]


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

    The value is plain text, not Markdown: ``*`` and ``<`` are kept as they
    are. Runs of whitespace, newlines included, become one space, as in an
    HTML paragraph. With ``collective.html2blocks`` installed, it builds the
    block, as it does for :func:`convert`; without it, the block is built
    here, the same way.

    :param value: The text.
    :returns: A ``slate`` block.
    """
    value = " ".join(value.split())
    try:
        from collective.html2blocks import converter
    except ImportError:
        return _paragraph(value)
    result = converter.volto_blocks(
        f"<p>{html.escape(value)}</p>", default_blocks=[], source_format="html"
    )
    found: list[dict[str, Any]] = [
        result["blocks"][block_id] for block_id in result["blocks_layout"]["items"]
    ]
    if len(found) == 1 and found[0].get("@type") == "slate":
        return found[0]
    # An empty paragraph converts to no block at all
    return _paragraph(value)


def _paragraph(value: str) -> dict[str, Any]:
    """A ``slate`` block with one paragraph, built without the converter.

    :param value: The text, with its whitespace already collapsed.
    :returns: The block.
    """
    return {
        "@type": "slate",
        "value": [{"type": "p", "children": [{"text": value}]}],
        "plaintext": value,
    }


def block(block_type: str, /, **data: Any) -> dict[str, Any]:
    """Any block, given its type and its data.

    For blocks this module has no helper for, such as those of an add-on.
    ``client.block_types`` describes the data each block of a site takes.

    :param block_type: The block's ``@type``, such as ``listing``.
    :param data: The block's data.
    :returns: The block.
    """
    return {**data, "@type": block_type}


def container(
    block_type: str, /, *items: Mapping[str, Any], **data: Any
) -> dict[str, Any]:
    """A block that holds other blocks, such as a grid.

    The blocks inside get their own ``blocks`` and ``blocks_layout``, as a
    page has; see :func:`build`.

    :param block_type: The block's ``@type``, such as ``gridBlock``.
    :param items: The blocks inside, in order.
    :param data: The container's own data, such as a ``headline``.
    :returns: The block.
    """
    return {**data, **build(*items), "@type": block_type}


def grid(*items: Mapping[str, Any], **data: Any) -> dict[str, Any]:
    """A Volto grid, which shows its blocks side by side.

    Volto allows up to four blocks in a grid, unless the site changes that.

    :param items: The blocks inside, in order, such as :func:`teaser` blocks.
    :param data: The grid's own data, such as a ``headline``.
    :returns: A ``gridBlock`` block.
    """
    return container("gridBlock", *items, **data)


def teaser(target: str, title: str = "", **data: Any) -> dict[str, Any]:
    """A teaser: a card linking to one item, with its title and image.

    The teaser shows the title, description, and image of the target, and
    follows later changes to it.

    :param target: Site path or URL of the item, or a URL outside the site.
    :param title: Title to store with the link.
    :param data: More data, such as ``overwrite`` and ``description``.
    :returns: A ``teaser`` block.
    """
    link = {"@id": target, "title": title} if title else {"@id": target}
    return block("teaser", href=[link], **data)


def normalize(item: Mapping[str, Any]) -> dict[str, Any]:
    """A block written by hand or by a model, in the shape Volto stores.

    A string ``href`` becomes the list of links that teasers, buttons and
    images keep (``[{"@id": …}]``). Blocks inside a container may be given
    as a list, in order: they get ids and a ``blocks_layout``. Blocks inside
    given as a mapping are normalized too, and their layout is tidied with
    :func:`tidy`.

    :param item: The block data.
    :returns: A new block.
    :raises ValueError: If the block, or one inside it, has no ``@type``.
    """
    if not isinstance(item, Mapping) or not item.get("@type"):
        raise ValueError(f"A block needs an @type: {item!r}")
    block = dict(item)
    if isinstance(block.get("href"), str):
        block["href"] = [{"@id": block["href"]}]
    children = block.get("blocks")
    if isinstance(children, list):
        block.update(build(*(normalize(child) for child in children)))
    elif isinstance(children, Mapping):
        found = {key: normalize(child) for key, child in children.items()}
        block.update(tidy(found, block.get("blocks_layout")))
    return block


def tidy(
    blocks: Mapping[str, Any], layout: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """``blocks`` and a ``blocks_layout`` that agree with each other.

    Layout ids that name no block are dropped, and so are repeated ones;
    blocks missing from the layout are added at the end. A title block is
    moved first, where Volto expects it. Other keys of the layout are kept.

    :param blocks: Block ids and their data.
    :param layout: The ``blocks_layout``, if any.
    :returns: ``blocks`` and ``blocks_layout``, as :func:`build` returns them.
    """
    order: list[str] = []
    for block_id in [*((layout or {}).get("items") or []), *blocks]:
        if block_id in blocks and block_id not in order:
            order.append(block_id)
    titles = [
        block_id
        for block_id in order
        if isinstance(blocks[block_id], Mapping)
        and blocks[block_id].get("@type") == "title"
    ]
    if titles:
        order.remove(titles[0])
        order.insert(0, titles[0])
    return {"blocks": dict(blocks), "blocks_layout": {**(layout or {}), "items": order}}


def locate(holder: Mapping[str, Any], block_id: str) -> dict[str, Any] | None:
    """What holds a block: an item, or the container block it is in.

    :param holder: The data of an item, or a block, with ``blocks``.
    :param block_id: Id of the block to find, at any depth.
    :returns: The mapping whose ``blocks`` holds the block, or ``None``.
    """
    found = holder.get("blocks")
    if not isinstance(found, dict):
        return None
    if block_id in found:
        return holder  # type: ignore[return-value]
    for block in found.values():
        if not isinstance(block, dict):
            continue
        # Containers keep their blocks either in themselves or in their data
        for inner in (block, block.get("data")):
            if isinstance(inner, dict):
                hit = locate(inner, block_id)
                if hit is not None:
                    return hit
    return None


#: Keys whose value is shown as the text of a block in :func:`outline`.
TEXT_KEYS = ("plaintext", "title", "headline", "alt")


def outline(
    blocks: Mapping[str, Any] | None,
    layout: Mapping[str, Any] | None = None,
    *,
    width: int = 60,
) -> list[dict[str, Any]]:
    """A short view of blocks: their ids, types and the start of their text.

    :param blocks: The ``blocks`` of an item or of a container block.
    :param layout: The matching ``blocks_layout``.
    :param width: Longest text to show.
    :returns: One entry per block, in layout order, with ``id``, ``@type``,
        maybe ``text``, and ``blocks`` for the blocks inside a container.
    """
    blocks = blocks or {}
    order = list((layout or {}).get("items") or [])
    order += [block_id for block_id in blocks if block_id not in order]
    entries = []
    for block_id in order:
        block = blocks.get(block_id)
        if not isinstance(block, dict):
            continue
        entry: dict[str, Any] = {"id": block_id, "@type": block.get("@type")}
        text = next(
            (block[key] for key in TEXT_KEYS if isinstance(block.get(key), str)), ""
        )
        text = " ".join(text.split())
        if text:
            entry["text"] = text if len(text) <= width else f"{text[: width - 1]}…"
        for holder in (block, block.get("data")):
            if isinstance(holder, dict) and isinstance(holder.get("blocks"), dict):
                entry["blocks"] = outline(holder["blocks"], holder.get("blocks_layout"))
        entries.append(entry)
    return entries


def prepare(data: Mapping[str, Any]) -> dict[str, Any]:
    """Field values whose blocks are normalized and tidied.

    ``blocks`` may be a list of blocks, in order, instead of a mapping: they
    get ids and a ``blocks_layout``, and a given ``blocks_layout`` is
    ignored. Each block goes through :func:`normalize`, and the layout
    through :func:`tidy`. Values without ``blocks`` are returned as they are.

    :param data: Field values of an item.
    :returns: New field values.
    :raises ValueError: If a block has no ``@type``.
    """
    found = data.get("blocks")
    if found is None:
        return dict(data)
    if isinstance(found, list):
        return {**data, **build(*(normalize(block) for block in found))}
    if not isinstance(found, Mapping):
        raise ValueError("blocks must be a list of blocks or a mapping of ids")
    normalized = {key: normalize(block) for key, block in found.items()}
    return {**data, **tidy(normalized, data.get("blocks_layout"))}


def convert(
    source: str,
    source_format: SourceFormat = "markdown",
    *,
    before: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Blocks for Markdown or HTML, converted by ``collective.html2blocks``.

    Paragraphs, headings, lists and quotes become text (``slate``) blocks;
    images, videos and tables get blocks of their own.

    Needs the ``markdown`` extra (Python 3.12 or later)::

        pip install 'plone-client[markdown]'

    :param source: The Markdown or HTML.
    :param source_format: ``markdown`` or ``html``.
    :param before: Blocks to put before the converted ones, such as
        :func:`title` and :func:`description`.
    :returns: ``blocks`` and ``blocks_layout``, as :func:`build` returns them.
    :raises PloneConfigurationError: If ``collective.html2blocks`` is not
        installed.
    :raises ValueError: If the format is unknown.
    """
    if source_format not in ("markdown", "html"):
        raise ValueError(f"Unknown source format: {source_format!r}")
    try:
        from collective.html2blocks import converter
    except ImportError:
        raise PloneConfigurationError(
            "Converting Markdown or HTML to blocks needs the 'markdown' extra, "
            "on Python 3.12 or later: pip install 'plone-client[markdown]'"
        ) from None
    result = converter.volto_blocks(
        source,
        default_blocks=[dict(block) for block in before],
        source_format=source_format,
    )
    return {"blocks": result["blocks"], "blocks_layout": result["blocks_layout"]}


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
