---
myst:
  html_meta:
    "description": "The functions of plone_client.blocks, with one example each: build blocks, convert Markdown, tidy a layout, and walk blocks and their links."
    "property=og:description": "The functions of plone_client.blocks, with one example each: build blocks, convert Markdown, tidy a layout, and walk blocks and their links."
    "property=og:title": "Block helpers"
---

(reference-blocks)=

# Block helpers

{mod}`plone_client.blocks` builds the {term}`blocks <block>` of {term}`Volto` pages, and walks the ones a site returns.
None of these functions sends a request.
{ref}`reference-content-model` describes the fields they produce, and {ref}`howto-any-block` shows them at work.

| Function | Returns |
|---|---|
| {func}`~plone_client.blocks.new_id` | A new block id. |
| {func}`~plone_client.blocks.build` | `blocks` and `blocks_layout` for blocks in order. |
| {func}`~plone_client.blocks.title` | A block that shows the title of the item. |
| {func}`~plone_client.blocks.description` | A block that shows the description of the item. |
| {func}`~plone_client.blocks.text` | A {term}`slate` block with one plain paragraph. |
| {func}`~plone_client.blocks.block` | Any block, from its type and its data. |
| {func}`~plone_client.blocks.container` | A block that holds other blocks. |
| {func}`~plone_client.blocks.grid` | A `gridBlock`. |
| {func}`~plone_client.blocks.teaser` | A card that links to one item. |
| {func}`~plone_client.blocks.convert` | Blocks for Markdown or HTML. |
| {func}`~plone_client.blocks.normalize` | A block in the shape Volto stores. |
| {func}`~plone_client.blocks.tidy` | `blocks` and a `blocks_layout` that agree. |
| {func}`~plone_client.blocks.prepare` | Field values with normalized blocks. |
| {func}`~plone_client.blocks.locate` | What holds a block. |
| {func}`~plone_client.blocks.outline` | A short view of blocks. |
| {func}`~plone_client.blocks.iter_blocks` | Every block, nested ones included. |
| {func}`~plone_client.blocks.iter_links` | Every link inside a value. |
| {func}`~plone_client.blocks.check_setting` | The shape of a `blocks` setting, checked. |
| {func}`~plone_client.blocks.merge_settings` | Several `blocks` settings, merged. |
| {func}`~plone_client.blocks.validate_setting` | A `blocks` setting, checked against the converter. |

<!-- check: start -->

## Build blocks

`new_id` and `build` give blocks new ids.

```python
from plone_client import blocks

print(len(blocks.new_id()))
page = blocks.build(blocks.title(), blocks.text("Hello!"))
print(sorted(page))
print([block["@type"] for block in page["blocks"].values()])
print(page["blocks_layout"]["items"] == list(page["blocks"]))
```

```text
36
['blocks', 'blocks_layout']
['title', 'slate']
True
```

`title`, `description`, and `text` build the blocks of a simple page.
`text` takes plain text, not Markdown, and collapses whitespace.

```python
from plone_client import blocks

print(blocks.title())
print(blocks.description())
print(blocks.text("Five *stars*\nand more."))
```

```text
{'@type': 'title'}
{'@type': 'description'}
{'@type': 'slate', 'plaintext': 'Five *stars* and more.', 'value': [{'type': 'p', 'children': [{'text': 'Five *stars* and more.'}]}]}
```

`block` builds any block from its `@type` and its data.

```python
from plone_client import blocks

print(blocks.block("listing", querystring={"query": [], "sort_on": "effective"}))
```

```text
{'querystring': {'query': [], 'sort_on': 'effective'}, '@type': 'listing'}
```

`teaser` links to one item, and `title` stores a title with the link.
Other keyword arguments become data of the block.

```python
from plone_client import blocks

print(blocks.teaser("/news/release-6-2", "Release", overwrite=True))
```

```text
{'href': [{'@id': '/news/release-6-2', 'title': 'Release'}], 'overwrite': True, '@type': 'teaser'}
```

`container` and `grid` hold other blocks in `blocks` and `blocks_layout`.
Keyword arguments become the data of the block itself.

```python
from plone_client import blocks

section = blocks.container("accordion", blocks.text("One."), headline="FAQ")
print(sorted(section), section["@type"], section["headline"])
row = blocks.grid(blocks.teaser("/news"), blocks.teaser("/about"))
print(row["@type"], len(row["blocks"]))
```

```text
['@type', 'blocks', 'blocks_layout', 'headline'] accordion FAQ
gridBlock 2
```

## Convert Markdown and HTML

`convert` needs the `markdown` extra, on Python 3.12 or later.
`before` adds blocks before the converted ones, and the second argument chooses `html`.

```python
from plone_client import blocks

page = blocks.convert("## Heading\n\nA paragraph.\n", before=[blocks.title()])
print([block["@type"] for block in page["blocks"].values()])
page = blocks.convert("<p>From <em>HTML</em>.</p>", "html")
print([block["plaintext"] for block in page["blocks"].values()])
```

```text
['title', 'slate', 'slate']
['From HTML.']
```

## Repair blocks

`normalize` accepts the shortcuts of hand-written blocks: a string `href`, and a list of blocks inside a container.

```python
from plone_client import blocks

print(blocks.normalize({"@type": "teaser", "href": "/news"}))
grid = blocks.normalize({"@type": "gridBlock", "blocks": [{"@type": "teaser", "href": "/news"}]})
print(len(grid["blocks"]), len(grid["blocks_layout"]["items"]))
```

```text
{'@type': 'teaser', 'href': [{'@id': '/news'}]}
1 1
```

`tidy` makes `blocks` and `blocks_layout` agree: it drops unknown and repeated ids, adds missing ones at the end, and moves the title first.

```python
from plone_client import blocks

found = {"a": {"@type": "slate"}, "b": {"@type": "title"}, "c": {"@type": "image"}}
print(blocks.tidy(found, {"items": ["a", "a", "gone", "b"]})["blocks_layout"])
```

```text
{'items': ['b', 'a', 'c']}
```

`prepare` applies both to the field values of an item, and takes `blocks` as a list.

```python
from plone_client import blocks

data = blocks.prepare({"title": "Hello", "blocks": [{"@type": "title"}]})
print(sorted(data), data["title"])
```

```text
['blocks', 'blocks_layout', 'title'] Hello
```

## Walk blocks

The examples below use a page with a grid inside.

<!-- check: file sample.py -->
```python
item = {
    "blocks": {
        "top": {"@type": "title"},
        "row": {
            "@type": "gridBlock",
            "headline": "Latest",
            "blocks": {"card": {"@type": "teaser", "href": [{"@id": "/news"}]}},
            "blocks_layout": {"items": ["card"]},
        },
    },
    "blocks_layout": {"items": ["top", "row"]},
}
```

`outline` gives a short view, `iter_blocks` goes through every block, depth first, `iter_links` finds the links, and `locate` finds what holds a block.

```python
from plone_client import blocks
from sample import item

print(blocks.outline(item["blocks"], item["blocks_layout"]))
print([block_id for block_id, _ in blocks.iter_blocks(item["blocks"], item["blocks_layout"])])
print(list(blocks.iter_links(item["blocks"])))
print(blocks.locate(item, "card")["@type"])
```

```text
[{'id': 'top', '@type': 'title'}, {'id': 'row', '@type': 'gridBlock', 'text': 'Latest', 'blocks': [{'id': 'card', '@type': 'teaser'}]}]
['top', 'row', 'card']
['/news']
gridBlock
```

## Choose block types

A `blocks` setting says which block types {func}`~plone_client.blocks.convert` produces.
Keys are block types, and values are `True`, `False`, or a mapping of options.
{ref}`howto-profiles` shows how to set it for a site.

```python
from plone_client import blocks

print(blocks.check_setting({"codeBlock": True}))
print(blocks.merge_settings({"codeBlock": True, "table": False}, {"codeBlock": False}))
print(blocks.validate_setting({"codeBlock": {"style": "light"}}))
try:
    blocks.check_setting({"codeBlock": "yes"})
except ValueError as error:
    print(error)
```

```text
{'codeBlock': True}
{'codeBlock': False, 'table': False}
{'codeBlock': {'style': 'light'}}
Setting of block type codeBlock must be true, false or a mapping of options, not 'yes'
```

<!-- check: stop -->

## Module

```{eval-rst}
.. automodule:: plone_client.blocks
```

## Related

- {ref}`reference-content-model` describes the blocks of an item.
- {ref}`howto-any-block` builds add-on blocks and grids.
- {ref}`reference-operations` edits the blocks of an item on a site.
