---
myst:
  html_meta:
    "description": "client.search and client.querystring: find items in the catalog."
    "property=og:description": "client.search and client.querystring: find items in the catalog."
    "property=og:title": "Search"
---

(reference-service-search)=

# Search

Find items through the catalog, with {class}`~plone_client.managers.search.SearchManager` and {class}`~plone_client.managers.search.QuerystringManager`.
The first takes keyword arguments and reads `@search`; the second takes the criteria a Listing block stores.
For queries over many items, see {ref}`howto-large-sites`.

Each example uses the `client` from {ref}`reference-services-reading`.

```{include} ../../_generated/services/search.md
```
