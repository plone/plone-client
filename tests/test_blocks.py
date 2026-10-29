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


def test_normalize_turns_a_string_href_into_links():
    block = blocks.normalize({"@type": "teaser", "href": "/news/a"})
    assert block == {"@type": "teaser", "href": [{"@id": "/news/a"}]}


def test_normalize_keeps_links():
    item = {"@type": "teaser", "href": [{"@id": "/news/a", "title": "A"}]}
    assert blocks.normalize(item) == item


def test_normalize_builds_a_list_of_children():
    grid = blocks.normalize({
        "@type": "gridBlock",
        "headline": "News",
        "blocks": [
            {"@type": "teaser", "href": "/news/a"},
            {"@type": "teaser", "href": "/news/b"},
        ],
    })
    ids = grid["blocks_layout"]["items"]
    assert grid["headline"] == "News"
    assert [grid["blocks"][i]["href"] for i in ids] == [
        [{"@id": "/news/a"}],
        [{"@id": "/news/b"}],
    ]


def test_normalize_tidies_a_mapping_of_children():
    grid = blocks.normalize({
        "@type": "gridBlock",
        "blocks": {"a": {"@type": "teaser", "href": "/a"}, "b": {"@type": "image"}},
        "blocks_layout": {"items": ["b", "gone"]},
    })
    assert grid["blocks_layout"] == {"items": ["b", "a"]}
    assert grid["blocks"]["a"]["href"] == [{"@id": "/a"}]


@pytest.mark.parametrize(
    "item",
    [
        {"href": "/a"},
        {"@type": ""},
        "slate",
        {"@type": "gridBlock", "blocks": [{"href": "/a"}]},
    ],
)
def test_normalize_needs_a_type(item):
    with pytest.raises(ValueError, match="needs an @type"):
        blocks.normalize(item)


def test_tidy_fixes_the_layout():
    found = {
        "t": {"@type": "title"},
        "a": {"@type": "slate"},
        "b": {"@type": "slate"},
    }
    layout = {"items": ["a", "missing", "a", "t"], "extra": 1}
    assert blocks.tidy(found, layout) == {
        "blocks": found,
        "blocks_layout": {"items": ["t", "a", "b"], "extra": 1},
    }


def test_tidy_without_layout_or_title():
    found = {"a": {"@type": "slate"}, "b": {"@type": "image"}}
    assert blocks.tidy(found)["blocks_layout"] == {"items": ["a", "b"]}


def nested_page():
    return {
        "blocks": {
            "t": {"@type": "title"},
            "g": {
                "@type": "gridBlock",
                "blocks": {"g1": {"@type": "teaser", "title": "First"}},
                "blocks_layout": {"items": ["g1"]},
            },
            "c": {
                "@type": "columns",
                "data": {
                    "blocks": {"c1": {"@type": "slate", "plaintext": "Column"}},
                    "blocks_layout": {"items": ["c1"]},
                },
            },
            "odd": "not a block",
        },
        "blocks_layout": {"items": ["t", "g", "c"]},
    }


@pytest.mark.parametrize(
    "block_id,holder",
    [
        ("t", lambda page: page),
        ("g1", lambda page: page["blocks"]["g"]),
        ("c1", lambda page: page["blocks"]["c"]["data"]),
    ],
)
def test_locate(block_id, holder):
    page = nested_page()
    assert blocks.locate(page, block_id) is holder(page)


def test_locate_misses():
    assert blocks.locate(nested_page(), "nope") is None
    assert blocks.locate({}, "nope") is None


def test_outline():
    page = nested_page()
    assert blocks.outline(page["blocks"], page["blocks_layout"]) == [
        {"id": "t", "@type": "title"},
        {
            "id": "g",
            "@type": "gridBlock",
            "blocks": [{"id": "g1", "@type": "teaser", "text": "First"}],
        },
        {
            "id": "c",
            "@type": "columns",
            "blocks": [{"id": "c1", "@type": "slate", "text": "Column"}],
        },
    ]


def test_outline_shortens_text():
    found = {"a": {"@type": "slate", "plaintext": "word " * 20}}
    entry = blocks.outline(found, width=10)[0]
    assert entry["text"] == "word word…"
    assert blocks.outline(None) == []


def test_prepare_builds_a_list():
    data = blocks.prepare({
        "title": "Hi",
        "blocks": [{"@type": "title"}, {"@type": "teaser", "href": "/a"}],
        "blocks_layout": {"items": ["ignored"]},
    })
    ids = data["blocks_layout"]["items"]
    assert data["title"] == "Hi"
    assert [data["blocks"][i]["@type"] for i in ids] == ["title", "teaser"]
    assert data["blocks"][ids[1]]["href"] == [{"@id": "/a"}]


def test_prepare_tidies_a_mapping():
    data = blocks.prepare({
        "blocks": {"a": {"@type": "slate"}, "t": {"@type": "title"}},
    })
    assert data["blocks_layout"] == {"items": ["t", "a"]}


def test_prepare_without_blocks():
    assert blocks.prepare({"title": "Hi"}) == {"title": "Hi"}


def test_prepare_refuses_other_blocks():
    with pytest.raises(ValueError, match="list of blocks"):
        blocks.prepare({"blocks": "slate"})


def test_check_setting():
    setting = {"codeBlock": {"style": "light"}, "slateTable": False}
    checked = blocks.check_setting(setting)
    assert checked == setting
    assert checked["codeBlock"] is not setting["codeBlock"]
    assert blocks.check_setting(None) == {}


@pytest.mark.parametrize(
    "setting,message",
    [
        (["codeBlock"], "must be a mapping"),
        ({"codeBlock": "yes"}, "true, false or a mapping"),
        ({"codeBlock": 1}, "true, false or a mapping"),
        ({"": True}, "named by strings"),
    ],
)
def test_check_setting_refuses(setting, message):
    with pytest.raises(ValueError, match=message):
        blocks.check_setting(setting)


def test_merge_settings_by_block_type():
    site = {"codeBlock": {"style": "dark"}, "slateTable": False}
    call = {"codeBlock": {"style": "light"}, "video": False}
    assert blocks.merge_settings(site, None, call) == {
        "codeBlock": {"style": "light"},
        "slateTable": False,
        "video": False,
    }
    assert blocks.merge_settings() == {}


def test_validate_setting_without_html2blocks(monkeypatch):
    monkeypatch.setitem(sys.modules, "collective.html2blocks", None)
    assert blocks.validate_setting({}) == {}
    with pytest.raises(PloneConfigurationError, match="'markdown' extra"):
        blocks.validate_setting({"codeBlock": True})


@needs_html2blocks
@pytest.mark.parametrize(
    "setting,message",
    [
        ({"nope": True}, "Unknown block type nope"),
        ({"codeBlock": {"colour": "red"}}, "Unknown option colour"),
        ({"slate": False}, "cannot be disabled"),
    ],
)
def test_validate_setting_refuses(setting, message):
    with pytest.raises(ValueError, match=message):
        blocks.validate_setting(setting)


CODE_AND_TABLE = "Hi\n\n```python\nprint(1)\n```\n\n| a | b |\n|---|---|\n| 1 | 2 |\n"


def _types(page):
    return [page["blocks"][i]["@type"] for i in page["blocks_layout"]["items"]]


@needs_html2blocks
@pytest.mark.parametrize(
    "setting,expected",
    [
        (None, ["slate", "slate", "slateTable"]),
        ({"codeBlock": True}, ["slate", "codeBlock", "slateTable"]),
        ({"slateTable": False}, ["slate", "slate", "slate"]),
    ],
)
def test_convert_with_a_setting(setting, expected):
    assert _types(blocks.convert(CODE_AND_TABLE, blocks=setting)) == expected


@needs_html2blocks
def test_convert_passes_options():
    page = blocks.convert(CODE_AND_TABLE, blocks={"codeBlock": {"style": "light"}})
    (code,) = [b for b in page["blocks"].values() if b["@type"] == "codeBlock"]
    assert (code["code"], code["language"], code["style"]) == (
        "print(1)",
        "python",
        "light",
    )
