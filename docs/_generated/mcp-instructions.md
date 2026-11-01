```text
Work with the content of Plone 6 sites through plone.restapi.

Paths are site paths such as /news/my-item; the @id URLs that tools return
work too. Read the @id of what a tool creates: Plone may change the id that
was asked for.

Content model, mostly for sites with the Volto frontend:
- The text of a page is in its blocks: `blocks` maps block ids to block
  data and `blocks_layout.items` lists them in order; a page without both
  shows nothing. Use `block_types` to learn which blocks the site has and
  the data each one takes. To write prose, prefer `create_page`, which
  converts Markdown to blocks.
- Wherever a tool takes blocks, give them as a list in order, each with an
  `@type`; ids and the layout are made for you, and a container such as a
  gridBlock may list its own `blocks` the same way. To change a page,
  `list_blocks` shows its block ids; then `add_blocks`, `update_block` and
  `remove_blocks` change only those blocks.
- Folder usually cannot be added, even though `content_types` lists it. For a
  section such as /news, create a Document (Page): it is folderish, and so is
  News Item. A dry run does not show that a type is refused, so check with
  `content_types` and `addable_in` first.
- A News Item has no `image` field: its lead image is `preview_image_link`, a
  relation to an Image stored inside it. Use `create_content_with_files`.
- Fields a type does not have are silently ignored. Check the schema with
  `content_types` before setting unusual fields.
- New items are private until a workflow transition such as `publish` runs.

Changes are refused when the server is read-only. In a dry run, nothing is
changed: tools return the requests they would have sent.
```
