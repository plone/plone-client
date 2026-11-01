---
myst:
  html_meta:
    "description": "client.types, client.block_types, and client.vocabularies."
    "property=og:description": "client.types, client.block_types, and client.vocabularies."
    "property=og:title": "Types and vocabularies"
---

(reference-service-types)=

# Types and vocabularies

Read the {term}`content types <content type>` of a site, the {term}`blocks <block>` it offers, and the valid values of its fields.
The examples that change a schema create a type of their own first, because the schema of a type must live in the site, not in code, to change it through the API.
`client.block_types` asks the {term}`Volto` server, so it needs {term}`frontend_url`; see {ref}`reference-managers-block-types`.

Each example uses the `client` from {ref}`reference-services-reading`.

```{include} ../../_generated/services/types.md
```
