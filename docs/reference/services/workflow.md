---
myst:
  html_meta:
    "description": "client.workflow, client.history, and client.working_copy."
    "property=og:description": "client.workflow, client.history, and client.working_copy."
    "property=og:title": "Workflow and history"
---

(reference-service-workflow)=

# Workflow and history

Move items through their {term}`workflow`, read their versions, and edit a published item in a working copy.
Each {term}`transition` changes the {term}`review_state` of an item.
Working copies need the `plone.app.iterate` add-on, which the examples on this page install first.

Each example uses the `client` from {ref}`reference-services-reading`.

```{include} ../../_generated/services/workflow.md
```
