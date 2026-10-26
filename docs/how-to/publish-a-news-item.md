---
myst:
  html_meta:
    "description": "Create and publish a news item with Volto blocks and a lead image, on Volto and Classic UI sites."
    "property=og:description": "Create and publish a news item with Volto blocks and a lead image, on Volto and Classic UI sites."
    "property=og:title": "Publish a news item with a lead image"
---

(howto-publish-news)=

# Publish a news item with a lead image

This guide shows you how to create a news item with blocks and a lead image, and publish it.

## Build the blocks

{mod}`plone_client.blocks` builds the `blocks` and `blocks_layout` fields of a Volto page.

```python
from plone_client import blocks

data = {
    "title": "Plone 6.2 is out",
    "description": "The release brings a new distribution.",
    **blocks.build(
        blocks.title(),
        blocks.description(),
        blocks.text("Plone 6.2 is out."),
    ),
}
item = client.content.create("/news", "News Item", data)
```

## Attach the lead image

Sites differ in where a news item keeps its lead image.
`plone.restapi` ignores fields that a content type does not have, so a wrong guess creates the item without an image and reports no error.
Read the content type's schema to know which field to set.

```python
fields = client.types.get("News Item")["properties"]
```

If the schema has an `image` field, as Classic UI sites do, send the image with the item.

```python
from plone_client import file_data

data["image"] = file_data("lead.jpg")
```

If it has `preview_image_link` instead, as Plone 6.1 sites created for Volto do, upload the image inside the item and link to it by UID.

```python
lead = client.files.upload(item["@id"], "lead.jpg")
client.content.update(item["@id"], preview_image_link=lead["UID"])
```

## Publish it

```python
client.workflow.transition(item["@id"], "publish")
```

To publish at a future date, pass `effective="2026-11-01T09:00:00"`.

## The complete script

The script reads the title, the description, and the paragraphs from a text file.
Without `--apply` it only prints the request it would send.

```shell
python publish_news.py news.txt /news --image lead.jpg
python publish_news.py news.txt /news --image lead.jpg --apply
```

```{literalinclude} ../_examples/publish_news.py
:language: python
```

## Related

- {ref}`howto-upload` uploads other files.
- {ref}`reference-python-api` documents {mod}`plone_client.blocks`.
