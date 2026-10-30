---
myst:
  html_meta:
    "description": "Build Volto blocks that plone-client has no helper for, such as add-on blocks, and blocks that hold other blocks, such as a grid of teasers."
    "property=og:description": "Build Volto blocks that plone-client has no helper for, such as add-on blocks, and blocks that hold other blocks, such as a grid of teasers."
    "property=og:title": "Build any block"
---

(howto-any-block)=

# Build any block

This guide shows you how to build Volto blocks that {mod}`plone_client.blocks` has no helper for, such as the blocks of an add-on, and blocks that hold other blocks, such as a grid.

## Learn the data a block takes

Each site has its own blocks, and each block its own data.
Ask the site before you build one.

```python
print(client.block_types.markdown("gridBlock"))
```

The `plone-client block-types gridBlock --markdown` command prints the same text.
If the site's Volto is older than 19.6.0, it has no `@blocks-schema` service, and you get the documentation of Volto's core blocks instead; see {ref}`reference-managers-block-types`.

## Build a block by its type

Pass the block's `@type` and its data to {func}`~plone_client.blocks.block`.

```python
from plone_client import blocks

page = blocks.build(
    blocks.title(),
    blocks.block("listing", querystring={"query": [], "sort_on": "effective"}),
)
client.content.create("/", "Document", title="Everything", **page)
```

## Build a grid of teasers

A grid shows up to four blocks side by side.
{func}`~plone_client.blocks.grid` holds the blocks you give it, and {func}`~plone_client.blocks.teaser` links to one item.

```python
paths = ["/news/one", "/news/two", "/news/three", "/news/four"]
page = blocks.build(
    blocks.title(),
    blocks.grid(*(blocks.teaser(path) for path in paths), headline="Latest news"),
)
client.content.create("/", "Document", title="Home", **page)
```

A teaser shows the title, description, and image of its item.
To show your own title instead, pass `overwrite=True` with a `title`.

## Build another block that holds blocks

For other blocks that keep their children in their own `blocks` and `blocks_layout`, such as an add-on's accordion, use {func}`~plone_client.blocks.container`.
Its keyword arguments become the data of the block itself.

```python
section = blocks.container(
    "accordion",
    blocks.text("Questions people ask."),
    blocks.teaser("/faq"),
    headline="FAQ",
)
```

Some blocks keep their children somewhere else, such as inside `data`.
Check the block's data with `client.block_types` first, and build those with {func}`~plone_client.blocks.block`.

## Related

- {ref}`reference-python-api` documents {mod}`plone_client.blocks`.
- {ref}`howto-publish-news` builds the blocks of a news item.
