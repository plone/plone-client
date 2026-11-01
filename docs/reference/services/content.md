---
myst:
  html_meta:
    "description": "client.content: read, create, update, delete, copy, move, order, and lock items."
    "property=og:description": "client.content: read, create, update, delete, copy, move, order, and lock items."
    "property=og:title": "Content"
---

(reference-service-content)=

# Content

Every {term}`content item` of a site, through {class}`~plone_client.managers.content.ContentManager`.
Methods take a {term}`ref`, so a path, a URL inside the site, or `uid:<UID>` all work.
A {term}`content type` decides which fields an item accepts; see {ref}`reference-content-model`.

Each example uses the `client` from {ref}`reference-services-reading`.

```{include} ../../_generated/services/content.md
```
