from plone_client import blocks
from plone_client.exceptions import PloneConfigurationError

import pytest
import sys
import uuid


def test_new_id_is_a_uuid():
    first, second = blocks.new_id(), blocks.new_id()
    assert first != second
    assert str(uuid.UUID(first)) == first


def test_build_keeps_order():
    page = blocks.build(blocks.title(), blocks.description(), blocks.text("Hi"))
    ids = page["blocks_layout"]["items"]
    assert len(ids) == 3
    assert [page["blocks"][i]["@type"] for i in ids] == [
        "title",
        "description",
        "slate",
    ]


needs_html2blocks = pytest.mark.skipif(
    sys.version_info < (3, 12), reason="collective.html2blocks needs Python 3.12"
)


def paragraph(value):
    return {
        "@type": "slate",
        "value": [{"type": "p", "children": [{"text": value}]}],
        "plaintext": value,
    }


TEXTS = [
    ("Hello", "Hello"),
    ("Not *Markdown* <b>nor HTML</b> & co", "Not *Markdown* <b>nor HTML</b> & co"),
    ("  two\nlines\t ", "two lines"),
    ("", ""),
]


@pytest.mark.parametrize("value,expected", TEXTS)
def test_text_block_without_html2blocks(monkeypatch, value, expected):
    monkeypatch.setitem(sys.modules, "collective.html2blocks", None)
    assert blocks.text(value) == paragraph(expected)


@needs_html2blocks
@pytest.mark.parametrize("value,expected", TEXTS)
def test_text_block_with_html2blocks(value, expected):
    assert blocks.text(value) == paragraph(expected)


@needs_html2blocks
def test_text_block_is_built_by_html2blocks(monkeypatch):
    from collective.html2blocks import converter

    sources = []
    original = converter.volto_blocks

    def spy(source, **kwargs):
        sources.append(source)
        return original(source, **kwargs)

    monkeypatch.setattr(converter, "volto_blocks", spy)
    blocks.text("a < b")
    assert sources == ["<p>a &lt; b</p>"]


@needs_html2blocks
def test_text_block_falls_back_on_unexpected_conversion(monkeypatch):
    from collective.html2blocks import converter

    monkeypatch.setattr(
        converter,
        "volto_blocks",
        lambda source, **kwargs: {
            "blocks": {"a": {"@type": "image"}},
            "blocks_layout": {"items": ["a"]},
        },
    )
    assert blocks.text("Hi") == paragraph("Hi")


def test_block_takes_any_type():
    assert blocks.block("myaddon.map", lat=1.5, zoom=3) == {
        "@type": "myaddon.map",
        "lat": 1.5,
        "zoom": 3,
    }


def test_container_holds_blocks():
    found = blocks.container(
        "accordion", blocks.text("a"), blocks.block("image"), headline="H"
    )
    assert found["@type"] == "accordion"
    assert found["headline"] == "H"
    ids = found["blocks_layout"]["items"]
    assert [found["blocks"][i]["@type"] for i in ids] == ["slate", "image"]


def test_grid_of_teasers():
    paths = ["/news/a", "/news/b", "/news/c", "/news/d"]
    page = blocks.build(
        blocks.title(),
        blocks.grid(*(blocks.teaser(path) for path in paths), headline="Latest"),
    )
    (_, grid_id) = page["blocks_layout"]["items"]
    grid = page["blocks"][grid_id]
    assert grid["@type"] == "gridBlock"
    assert grid["headline"] == "Latest"
    teasers = [grid["blocks"][i] for i in grid["blocks_layout"]["items"]]
    assert teasers[0] == {"@type": "teaser", "href": [{"@id": "/news/a"}]}
    assert [
        b["@type"] for _, b in blocks.iter_blocks(page["blocks"], page["blocks_layout"])
    ] == [
        "title",
        "gridBlock",
        "teaser",
        "teaser",
        "teaser",
        "teaser",
    ]
    assert list(blocks.iter_links(page["blocks"])) == paths


def test_teaser_options():
    assert blocks.teaser(
        "https://plone.org", "Plone", overwrite=True, description="CMS"
    ) == {
        "@type": "teaser",
        "href": [{"@id": "https://plone.org", "title": "Plone"}],
        "overwrite": True,
        "description": "CMS",
    }


def test_iter_blocks_follows_layout_and_nesting():
    item = {
        "blocks": {
            "b": {"@type": "slate"},
            "a": {"@type": "title"},
            "grid": {
                "@type": "gridBlock",
                "blocks": {"g1": {"@type": "image"}},
                "blocks_layout": {"items": ["g1"]},
            },
            "cols": {
                "@type": "columnsBlock",
                "data": {
                    "blocks": {"c1": {"@type": "teaser"}},
                    "blocks_layout": {"items": ["c1"]},
                },
            },
            "orphan": {"@type": "html"},
        },
        "blocks_layout": {"items": ["a", "b", "grid", "cols", "missing"]},
    }
    visited = [
        block_id
        for block_id, _ in blocks.iter_blocks(item["blocks"], item["blocks_layout"])
    ]
    assert visited == ["a", "b", "grid", "g1", "cols", "c1", "orphan"]


def test_iter_blocks_handles_empty():
    assert list(blocks.iter_blocks(None, None)) == []


def test_iter_links():
    block = {
        "@type": "teaser",
        "href": [{"@id": "/news/item", "title": "Item"}],
        "preview_image_link": "../resolveuid/abc",
        "value": [
            {
                "type": "p",
                "children": [
                    {
                        "type": "link",
                        "data": {"url": "https://example.org"},
                        "children": [],
                    }
                ],
            }
        ],
        "title": "not a link",
    }
    assert list(blocks.iter_links(block)) == [
        "/news/item",
        "../resolveuid/abc",
        "https://example.org",
    ]


def test_convert_needs_html2blocks(monkeypatch):
    monkeypatch.setitem(sys.modules, "collective.html2blocks", None)
    with pytest.raises(PloneConfigurationError, match="'markdown' extra"):
        blocks.convert("# Hi")


def test_convert_refuses_unknown_formats():
    with pytest.raises(ValueError, match="Unknown source format"):
        blocks.convert("Hi", "rst")  # type: ignore[arg-type]


@needs_html2blocks
def test_convert_markdown():
    page = blocks.convert("Hello *you*", before=[blocks.title()])
    types = [page["blocks"][i]["@type"] for i in page["blocks_layout"]["items"]]
    assert types == ["title", "slate"]
    assert set(page) == {"blocks", "blocks_layout"}
