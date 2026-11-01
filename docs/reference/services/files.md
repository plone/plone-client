---
myst:
  html_meta:
    "description": "client.files: upload, replace, and download files and images."
    "property=og:description": "client.files: upload, replace, and download files and images."
    "property=og:title": "Files"
---

(reference-service-files)=

# Files

Store and read files and images, which are items of the types `File` and `Image`.
`upload` and `replace` send the file inside a JSON body, and the `tus_` methods send it in chunks.
For a guide, see {ref}`howto-upload`.

Each example uses the `client` from {ref}`reference-services-reading`.

```{include} ../../_generated/services/files.md
```
