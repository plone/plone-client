---
myst:
  html_meta:
    "description": "Upload, replace, and download files and images with plone-client."
    "property=og:description": "Upload, replace, and download files and images with plone-client."
    "property=og:title": "Upload and download files"
---

(howto-upload)=

# Upload and download files

This guide shows you how to move files and images in and out of a site, from Python and from the command line.

## Upload a file

```python
image = client.files.upload("/images", "photo.jpg", title="A photo")
document = client.files.upload("/files", "report.pdf")
```

{meth}`~plone_client.managers.files.FilesManager.upload` creates an `Image` for image files and a `File` for anything else.
The file travels base64-encoded inside one JSON request.

From the command line, upload several files at once.

```shell
plone-client upload /images photo.jpg logo.png
```

## Upload a large file

For large files, upload in chunks with TUS.

```python
video_url = client.files.tus_upload("/files", "talk.mp4")
```

{meth}`~plone_client.managers.files.FilesManager.tus_upload` returns the URL of the new item.

```shell
plone-client upload /files talk.mp4 --tus
```

## Replace the file of an item

```python
client.files.replace(document["@id"], "report-2.pdf")
client.files.replace(image["@id"], "photo-2.jpg", field="image")
client.files.tus_replace(video_url, "talk-2.mp4")
```

`replace()` writes the `file` field unless given another one, so pass `field="image"` for images.

## Set a file field on another content type

{func}`~plone_client.managers.files.file_data` builds the value `plone.restapi` expects for any file or image field.
This example sets the `image` field of a news item on a Classic UI site.

```python
from plone_client import file_data

client.content.update("/news/hello", image=file_data("lead.jpg"))
```

`plone.restapi` ignores a field that the content type does not have, without reporting an error.
Check the type's schema with `client.types.get("News Item")["properties"]` first, as {ref}`howto-publish-news` does.

## Download a file

```python
pdf = client.files.download("/files/report.pdf")
photo = client.files.download("/images/photo.jpg", field="image")
```

The command line picks the `image` field for `Image` items by itself.

```shell
plone-client download /images/photo.jpg -o photo.jpg
```

## Related

- {ref}`howto-publish-news` attaches a lead image to a news item.
- {ref}`reference-managers` documents {class}`~plone_client.managers.files.FilesManager`.
