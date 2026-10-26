from plone_client import blocks

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


def test_text_block():
    block = blocks.text("Hello")
    assert block == {
        "@type": "slate",
        "value": [{"type": "p", "children": [{"text": "Hello"}]}],
        "plaintext": "Hello",
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
