---
myst:
  html_meta:
    "description": "Create pages from Markdown, items with their images, and whole folders of files with one call each, from Python or the command line."
    "property=og:description": "Create pages from Markdown, items with their images, and whole folders of files with one call each, from Python or the command line."
    "property=og:title": "Create content in one step"
---

(howto-operations)=

# Create content in one step

This guide shows you how to use the operations of {mod}`plone_client.operations`, which each send several requests in the right order: create a page from Markdown, create an item with its images, upload a folder, and copy or move content with a report.
Every operation is also a command of the command line.

## Create a page from Markdown

Install the `markdown` extra, which needs Python 3.12 or later.

```shell
uv add "plone-client[markdown]"
```

Pass the Markdown, and the folder to create the page in.
A leading `#` heading becomes the title.

::::{tab-set}
:sync-group: interface

:::{tab-item} Python
:sync: python

```python
from pathlib import Path
from plone_client import operations

result = operations.create_page(
    client, "/docs", Path("getting-started.md").read_text(), publish="publish"
)
print(result.item["@id"])
```
:::

:::{tab-item} Command line
:sync: shell

```shell
plone-client create-page /docs getting-started.md --publish publish
```
:::
::::

For HTML, pass `source_format="html"` in Python, or `--html` on the command line; a file ending in `.html` is read as HTML.
To give the title yourself, pass `title`, or `--title`.

## Create an item with its images

Pass the files to upload inside the item.
The first image becomes the lead image, stored the way the type expects: in its `image` field, or in `preview_image_link`, as News Items on Volto sites do.

::::{tab-set}
:sync-group: interface

:::{tab-item} Python
:sync: python

```python
result = operations.create_with_files(
    client,
    "/news",
    "News Item",
    ["lead.jpg", "inside.jpg", "plan.pdf"],
    title="Our new office",
    publish="publish",
)
```
:::

:::{tab-item} Command line
:sync: shell

```shell
plone-client create-with-files /news "News Item" lead.jpg inside.jpg plan.pdf --title "Our new office" --publish publish
```
:::
::::

To pick another lead image, pass its index in `lead_image`, counting from 0, or its position with `--lead`, counting from 1.
To set none, pass `lead_image=None` (`--no-lead`).

## Upload a folder

The contents of the local folder go inside the site's folder: subfolders become pages, images become `Image` items, and other files `File` items.
With `convert_pages` (`--pages`), Markdown and HTML files become pages, and a folder's `index.md` or `README.md` becomes the content of the folder's page.

::::{tab-set}
:sync-group: interface

:::{tab-item} Python
:sync: python

```python
result = operations.upload_tree(client, "handbook", "/docs", convert_pages=True)
for entry in result.created:
    print(entry["source"], "->", entry["@id"])
```
:::

:::{tab-item} Command line
:sync: shell

```shell
plone-client upload-tree handbook /docs --pages
```
:::
::::

Files and folders whose names start with a dot are left out, unless you pass `include_hidden=True` (`--hidden`).

## Copy or move a folder

{func}`~plone_client.operations.copy_items` and {func}`~plone_client.operations.move_items` report where each item went and how many items it holds, before and after.

```python
result = operations.copy_items(client, "/news/2025", "/archive")
for entry in result.created:
    print(entry["@id"], entry["items"], entry["items_after"])
```

Plone renames a copy whose id is taken, so read the new `@id` from the result.

## Preview an operation

Run it with a `dry_run` client, or pass `-n` on the command line.
The result lists the requests it would send, and the items it would create, with `"planned": true` and the path they would most likely get.

```shell
plone-client -n upload-tree handbook /docs --pages
```

## Recover from a failure part way

When a request fails, the operation stops and raises {class}`~plone_client.exceptions.PloneOperationError`.
Its `result` lists what was already created, so you can remove it or carry on from there.

```python
from plone_client import PloneOperationError

try:
    operations.upload_tree(client, "handbook", "/docs")
except PloneOperationError as error:
    for entry in error.result.created:
        print("created before the failure:", entry["@id"])
    raise
```

On the command line, the error on standard error has the same `result`.

## Related

- {ref}`reference-operations` lists the requests of each operation.
- {ref}`howto-publish-news` shows the steps behind `create_with_files`.
- {ref}`howto-preview-changes` previews other changes.
