---
myst:
  html_meta:
    "description": "Keep plone-client scripts fast on sites with many items: batching, metadata fields, catalog entries against full items, and the cost of a UID reference."
    "property=og:description": "Keep plone-client scripts fast on sites with many items: batching, metadata fields, catalog entries against full items, and the cost of a UID reference."
    "property=og:title": "Work with large sites"
---

(howto-large-sites)=

# Work with large sites

This guide shows you how to keep a script fast on a {term}`Plone` site with many items.
The rule is to ask the catalog, which answers from an index, and to read a full {term}`content item` only when you need one.

The examples run on the sample content of {ref}`howto-run-a-site`.
Each one counts its requests with {meth}`~plone_client.PloneClient.recording`, which you can use to measure your own scripts.

<!-- check: start -->

## Count before you fetch

To know how many items match, use {meth}`~plone_client.managers.search.SearchManager.count`, which asks for one result.

```python
from plone_client import PloneClient

client = PloneClient("http://localhost:8080/Plone", username="admin", password="admin")
with client.recording() as requests:
    total = client.search.count("/news", portal_type="News Item", review_state="private")
print(total, "items,", len(requests), "request")
```

```text
2 items, 1 request
```

## Let the iterators fetch the pages

The site answers a search in batches of 25 by default.
{meth}`~plone_client.managers.search.SearchManager.search` returns one batch, and {meth}`~plone_client.managers.search.SearchManager.iter` follows them all.
`iter` asks for 100 items per request, and `b_size` changes that.
`limit` stops early.

```python
from plone_client import PloneClient

client = PloneClient("http://localhost:8080/Plone", username="admin", password="admin")
page = client.search.search("/news", portal_type="News Item", b_size=2)
print(len(page["items"]), "of", page["items_total"])

with client.recording() as requests:
    items = list(client.search.iter("/news", portal_type="News Item", b_size=2))
print(len(items), "items,", len(requests), "requests")

with client.recording() as requests:
    items = list(client.search.iter("/news", portal_type="News Item", limit=2))
print(len(items), "items,", len(requests), "request")
```

```text
2 of 5
5 items, 3 requests
2 items, 1 request
```

## Ask for the metadata you need

A catalog entry has a few fields by default.
It has no `UID`, `id`, or `modified` unless you ask for them with `metadata_fields`.

```python
from plone_client import PloneClient

client = PloneClient("http://localhost:8080/Plone", username="admin", password="admin")
entry = next(client.search.iter("/news", portal_type="News Item"))
print(sorted(entry))
fields = ("UID", "modified")
entry = next(client.search.iter("/news", portal_type="News Item", metadata_fields=fields))
print("UID" in entry, "modified" in entry)
```

```text
['@id', '@type', 'description', 'effective', 'end', 'getObjSize', 'getRemoteUrl', 'head_title', 'image_field', 'image_scales', 'mime_type', 'nav_title', 'review_state', 'start', 'title', 'type_title']
True True
```

`metadata_fields="_all"` returns every column, and costs more bytes for each item.
Metadata comes from the catalog and takes one request per batch, however many columns you ask for.
`fullobjects=True` makes the site serialize each item in full, which is much slower.

## Read a folder without reading its items

{meth}`~plone_client.managers.content.ContentManager.get` on a folder also lists the first items inside it.
Pass `include_items=False` when you only want the folder.
{meth}`~plone_client.managers.content.ContentManager.children` lists a folder through the catalog, in the folder's order.

```python
from plone_client import PloneClient

client = PloneClient("http://localhost:8080/Plone", username="admin", password="admin")
print(len(client.content.get("/news")["items"]))
print("items" in client.content.get("/news", include_items=False))
with client.recording() as requests:
    names = [entry["title"] for entry in client.content.children("/news", portal_type="News Item")]
print(names[0], len(names), len(requests))
```

```text
5
False
Release 6.2 is out 5 1
```

Avoid one `content.get` for each search result.
Compare only what the entry has, and read the full item when it differs, as {ref}`howto-sync` does.

## Use paths when you have them

A {term}`ref` of the form `uid:<UID>` costs one extra `@search` request, each time, because the client looks up the path first.
When you work on the same item several times, resolve it once.

```python
from plone_client import PloneClient

client = PloneClient("http://localhost:8080/Plone", username="admin", password="admin")
uid = client.content.get("/about")["UID"]
with client.recording() as requests:
    client.content.get(f"uid:{uid}", include_items=False)
print(len(requests), "requests with a UID")

path = client.content.resolve(f"uid:{uid}")
with client.recording() as requests:
    client.content.get(path, include_items=False)
print(len(requests), "request with a path")
```

```text
2 requests with a UID
1 request with a path
```

<!-- check: stop -->

## Keep long jobs safe

Requests that fail because of a dropped connection or an overloaded site are retried, except `POST`; see {ref}`reference-client`.
A job that creates many items should be able to run again: skip what exists, as {ref}`tutorial-first-script` does, so a failure halfway costs nothing.

## Related

- {ref}`reference-service-search` lists every search argument.
- {ref}`howto-sync` compares catalog entries with records.
- {ref}`explanation-direct-api` explains when to call a service directly.
