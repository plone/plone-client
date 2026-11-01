---
myst:
  html_meta:
    "description": "How plone-client sees the content of a Plone site: folders, fields, blocks, lead images, workflow states, dates, and links."
    "property=og:description": "How plone-client sees the content of a Plone site: folders, fields, blocks, lead images, workflow states, dates, and links."
    "property=og:title": "Content model"
---

(reference-content-model)=

# Content model

This page describes the shape of content on a {term}`Plone` 6 site as `plone.restapi` returns it, and as plone-client writes it.
The answers below come from the {term}`Compose site`, a site created for {term}`Volto` on Plone 6.1.
Other sites can have other {term}`content types <content type>` and fields; `client.types.get()` tells you what a site has.

<!-- check: start -->

## Content types

The `Page` type has the id `Document`.
On a Volto site, `Folder` exists but cannot be added, and `Document` and `News Item` are {term}`folderish`.

```python
from plone_client import PloneClient

client = PloneClient("http://localhost:8080/Plone", username="admin", password="admin")
for item in client.types.list():
    print(item["title"], item["addable"])
print(client.types.addable("/news"))
print(client.content.get("/news")["is_folderish"])
print(client.content.get("/news/release-6-2")["is_folderish"])
```

```text
Collection False
Event True
File True
Folder False
Image True
Link True
News Item True
Page True
['Event', 'File', 'Image', 'Link', 'News Item', 'Document']
True
True
```

| Field of `@types` | Meaning |
|---|---|
| `title` | The title people see, which can differ from the id. |
| `addable` | Whether this user can add the type at this path. |

{meth}`~plone_client.managers.types.TypesManager.addable` returns the ids to pass to {meth}`~plone_client.managers.content.ContentManager.create`.

## Fields

Each type has a JSON schema, which lists its fields in `properties`.

```python
from plone_client import PloneClient

client = PloneClient("http://localhost:8080/Plone", username="admin", password="admin")
for portal_type in ("Document", "News Item", "Image", "File"):
    fields = client.types.get(portal_type)["properties"]
    print(portal_type, [name for name in ("blocks", "image", "file", "preview_image_link") if name in fields])
```

```text
Document ['blocks', 'preview_image_link']
News Item ['blocks', 'preview_image_link']
Image ['image']
File ['file', 'preview_image_link']
```

`plone.restapi` silently ignores a field that the type does not have, and answers with success.

```python
from plone_client import PloneClient

client = PloneClient("http://localhost:8080/Plone", username="admin", password="admin")
item = client.content.create("/", "Document", id="ignored", title="Ignored", colour="red")
print(item["title"], "colour" in item)
client.content.delete("/ignored")
```

```text
Ignored False
```

## Blocks

An item with blocks stores its content in two fields.

| Field | Content |
|---|---|
| `blocks` | A mapping of block ids to {term}`block` data, each with an `@type`. |
| `blocks_layout` | `items`, the list of block ids in display order. |

Volto shows a page without both as empty.
{meth}`~plone_client.managers.content.ContentManager.create` sends what you give it, so it adds no blocks.
The `create` command, the `create_content` tool, and the operations add a title block and a description block; see {ref}`reference-operations`.

`build` returns both fields with new ids.

```python
from plone_client import blocks

import json


page = blocks.build(blocks.title(), blocks.description(), blocks.text("Hello!"))
print(json.dumps(list(page["blocks"].values()), indent=2))
print(sorted(page), len(page["blocks_layout"]["items"]))
```

```text
[
  {
    "@type": "title"
  },
  {
    "@type": "description"
  },
  {
    "@type": "slate",
    "plaintext": "Hello!",
    "value": [
      {
        "type": "p",
        "children": [
          {
            "text": "Hello!"
          }
        ]
      }
    ]
  }
]
['blocks', 'blocks_layout'] 3
```

The `title` and `description` blocks hold no text: they show the fields of the item.

A block that holds others keeps `blocks` and `blocks_layout` of its own, as `gridBlock` does.
Some add-on blocks keep them inside `data`, and the walking helpers of {ref}`reference-blocks` follow both.

### The slate value

The `value` of a {term}`slate` block is a list of nodes, each with a `type` and `children`, down to objects with `text`.
`plaintext` repeats the text without markup.

```python
from plone_client import blocks

import json


page = blocks.convert("Plain and **bold**.\n\n- One item\n")
print(json.dumps([block["value"] for block in page["blocks"].values()], indent=2))
```

```text
[
  [
    {
      "type": "p",
      "children": [
        {
          "text": "Plain and "
        },
        {
          "type": "strong",
          "children": [
            {
              "text": "bold"
            }
          ]
        },
        {
          "text": "."
        }
      ]
    }
  ],
  [
    {
      "type": "ul",
      "children": [
        {
          "type": "li",
          "children": [
            {
              "text": "One item"
            }
          ]
        }
      ]
    }
  ]
]
```

## Lead image

Where an item keeps its {term}`lead image` depends on the site.

| Site | Field | Value |
|---|---|---|
| Created for Volto | `preview_image_link` | A relation to an `Image`, usually stored inside the item. Send the `UID` of the image. |
| Classic UI | `image` | The image itself. |

The same `News Item` type has either one, so read the schema.
{func}`~plone_client.operations.create_with_files` does this for you.

```python
from plone_client import PloneClient
from plone_client import file_data
from seed import png

client = PloneClient("http://localhost:8080/Plone", username="admin", password="admin")
image = client.files.upload("/news/release-6-2", png(0, 90, 0), filename="lead.png")
item = client.content.update("/news/release-6-2", preview_image_link=image["UID"])
link = item["preview_image_link"]
print(link["@id"], link["@type"], link["title"])
```

```text
http://localhost:8080/Plone/news/release-6-2/lead.png Image lead.png
```

You send a `UID`, and the site answers with an object.

An `Image` keeps its file in the `image` field and a `File` in the `file` field.
Each answers with `content-type`, `filename`, `size`, and a `download` URL, and an image also with `width`, `height`, and `scales`.

## Workflow

The {term}`workflow` of a site decides the {term}`review_state` of each item.
New items start `private`, and only people with a role on them can see them.

```python
from plone_client import PloneClient

site = PloneClient("http://localhost:8080/Plone", username="admin", password="admin")
visitor = PloneClient("http://localhost:8080/Plone")
for item in site.search.iter("/news", portal_type="News Item", sort_on="sortable_title"):
    print(item["review_state"], item["title"])
print("Visitors see", visitor.search.count("/news", portal_type="News Item"))
print(site.workflow.get("/news/release-party")["transitions"][0]["title"])
```

```text
published Old announcement
published Release 6.2 is out
private Release notes draft
private Release party in Brasília
pending Sprint report
Visitors see 2
Publish
```

`Image` and `File` items have no workflow: their `review_state` is `null`, and they follow the item that holds them.

## Dates

| Field | Meaning |
|---|---|
| `created`, `modified` | Set by the site. |
| `effective` | The publication date. Publishing sets it when it is empty. |
| `expires` | The date the item stops appearing in searches for visitors. |

The site refuses an `expires` date before the `effective` date.

```python
from plone_client import PloneClient

site = PloneClient("http://localhost:8080/Plone", username="admin", password="admin")
visitor = PloneClient("http://localhost:8080/Plone")
print(site.content.get("/news/release-party")["effective"])
print(visitor.search.count("/news", portal_type="News Item"))
dates = {"effective": "2019-01-01T00:00:00", "expires": "2020-01-01T00:00:00"}
site.content.update("/news/old-announcement", dates)
print(site.content.get("/news/old-announcement")["review_state"])
print(visitor.search.count("/news", portal_type="News Item"))
```

```text
None
2
published
1
```

## Links between items

Each {term}`content item` has a {term}`UID`, which stays the same when the item moves.
{term}`resolveuid` links point to the UID, and Volto stores internal links that way.
Everything in plone-client that takes a {term}`ref` accepts both forms.

```python
from plone_client import PloneClient
from plone_client.utils import resolveuid_url

client = PloneClient("http://localhost:8080/Plone", username="admin", password="admin")
uid = client.content.get("/about/team")["UID"]
link = resolveuid_url(uid)
print(link)
print(client.content.resolve(f"uid:{uid}"))
print(client.content.resolve(link))
```

```text
../resolveuid/b04bfdfc710c462cac035ca85edd3b37
/about/team
/about/team
```

<!-- check: stop -->

## Related

- {ref}`reference-blocks` lists the block helpers.
- {ref}`reference-operations` creates items with their blocks, files, and lead image.
- {ref}`howto-publish-news` applies this to a news item.
- {ref}`reference-compatibility` lists the Plone versions.
