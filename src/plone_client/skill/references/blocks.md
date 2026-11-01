# Blocks

Read this before you write or change the blocks of a page on a Volto site.

## Pick the simplest way

| Goal | Use |
|---|---|
| Write a page from prose | `plone-client create-page`, which converts Markdown or HTML to blocks. |
| Change a title or another field | `plone-client update`; the blocks stay as they are. |
| Add, change, or reorder blocks | Read the blocks, edit them, and write them back, as shown below. |
| Show a block Markdown cannot express, such as a grid | Write its JSON by hand, after you read its documentation. |

## How a page stores blocks

Two fields hold the content, and a page needs both.

- `blocks` maps ids to block data, and each block has an `@type`.
- `blocks_layout.items` lists the ids in display order.

Ids are any unique strings.
Every id in `blocks` must also be in `blocks_layout.items`.
A block that is missing from the layout stays stored, and Volto does not show it, although `plone-client blocks` still lists it.

## Learn what the site offers

Each site has its own blocks, and each block has its own data, so ask before you write one.

```shell
plone-client block-types --markdown                  # the blocks of the site
plone-client block-types gridBlock --markdown        # the data one block takes
plone-client block-types --for /news/item --markdown # what editors can add to this item
```

If the answer has `"source": "builtin"`, or a warning about `@blocks-schema`, it describes only Volto's core blocks, and the site did not say which blocks it has.
This happens on Volto before 19.6, or when the profile has no frontend URL.
Tell the user before you rely on a block from an add-on.

## Read the blocks

```shell
plone-client blocks /news/item                 # ids, types, and text, nested blocks included
plone-client blocks /news/item --links         # the links in each block
plone-client get /news/item -f blocks,blocks_layout > page.json   # the full data
```

## Create a page from JSON

Give `blocks` as a mapping, with `blocks_layout`.
The command line refuses a list of blocks with exit code 6 and `Wrong contained type`.

```json
{
  "blocks": {
    "title-1": {"@type": "title"},
    "text-1": {
      "@type": "slate",
      "value": [{"type": "p", "children": [{"text": "First paragraph."}]}],
      "plaintext": "First paragraph."
    }
  },
  "blocks_layout": {"items": ["title-1", "text-1"]}
}
```

```shell
plone-client create /docs Document --title "Page" -d @page.json
```

With `blocks` in the data, `create` adds no title or description block, so include the ones you want.
A page normally has exactly one `title` block.

## Change the blocks

`update` replaces all the blocks, so a file with one block leaves a page with one block.
Always start from what the site has.

1. Read the page: `plone-client get /docs/page -f blocks,blocks_layout > page.json`.
2. Edit `page.json`: change a block, or add one to `blocks` and its id to `blocks_layout.items`.
3. Preview it, if the site is not a local one: `plone-client -n update /docs/page -d @page.json`.
4. Write it: `plone-client update /docs/page -d @page.json`.
5. Check the result: `plone-client blocks /docs/page`.

To reorder blocks, send only the layout.

```shell
plone-client update /docs/page -s 'blocks_layout:={"items": ["text-1", "title-1"]}'
```

## Common blocks

Text is a `slate` block, with one paragraph, heading, list, or quote in each block.
Keep `plaintext` in sync with `value`, because the site indexes it for search.

```json
{
  "@type": "slate",
  "value": [{"type": "h2", "children": [{"text": "Our services"}]}],
  "plaintext": "Our services"
}
```

A teaser links to one item, and shows its title, description, and image.

```json
{"@type": "teaser", "href": [{"@id": "/news/item", "title": "Item"}]}
```

A grid holds up to four blocks in its own `blocks` and `blocks_layout`, and those need their ids too.
For the others, and for inline formatting and links in text, read `plone-client block-types <block> --markdown`.

## From Python or MCP

These helpers exist only outside the command line.

- The `plone_client.blocks` module builds blocks with new ids and a layout: `build`, `title`, `description`, `text`, `block`, `grid`, `teaser`, and `container`.
- The MCP tools take blocks as a list, make the ids and the layout, and change one block at a time with `add_blocks`, `update_block`, and `remove_blocks`.
