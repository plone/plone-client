---
myst:
  html_meta:
    "description": "The high-level operations of plone_client.operations: the requests of each one, the result it returns, and how it behaves in a dry run."
    "property=og:description": "The high-level operations of plone_client.operations: the requests of each one, the result it returns, and how it behaves in a dry run."
    "property=og:title": "Operations"
---

(reference-operations)=

# Operations

An {term}`operation` of {mod}`plone_client.operations` is a task of several requests, sent in the right order for the {term}`content type` at hand.
{ref}`howto-operations` shows how to use them.

## Requests

| Function | Requests, in order |
|---|---|
| {func}`~plone_client.operations.create_with_files` | `GET @types/<type>`, create the item, one upload per file, `PATCH preview_image_link` when the type keeps its lead image there, the transition, and `GET` of the item. |
| {func}`~plone_client.operations.create_page` | Create the page, one upload per file and `PATCH preview_image_link` when the lead image goes there, then the transition and `GET` of the page. |
| {func}`~plone_client.operations.upload_tree` | `GET` of the folder, then one create or upload per entry, depth first, and a transition after each new page. |
| {func}`~plone_client.operations.copy_items`, {func}`~plone_client.operations.move_items` | `GET` of the folder, a `@search` count per item, `@copy` or `@move`, and a `@search` count per new item. |
| {func}`~plone_client.operations.add_blocks`, {func}`~plone_client.operations.update_block`, {func}`~plone_client.operations.remove_blocks`, {func}`~plone_client.operations.set_blocks` | `GET` of the item, then one `PATCH` with all its `blocks` and `blocks_layout`. They take no lock, so a change someone else saves between the two is lost. |

Transitions run only when `publish` is given.

## Result

Every operation returns an {class}`~plone_client.operations.OperationResult`.

| Field | Content |
|---|---|
| `operation` | The name of the operation. |
| `dry_run` | Whether the requests that change the site were skipped. |
| `item` | The main item, for operations that create one. |
| `created` | The items created, in order. `source` names the local file or folder, and `planned` marks a path guessed in a dry run. |
| `changed` | The items changed, with what changed. |
| `requests` | Every request sent or skipped: `method`, `url`, `status`, and `dry_run` when skipped. |
| `error` | The error that stopped the operation, only when there is one. |

`to_dict()` returns the same fields as JSON-ready data.
The command line and the {term}`MCP` tools print it.

<!-- check: start -->

```python
from plone_client import operations
from plone_client import PloneClient
from pathlib import Path
from seed import png

import json


Path("lead.png").write_bytes(png(0, 90, 0))
with PloneClient("http://localhost:8080/Plone", username="admin", password="admin") as client:
    result = operations.create_with_files(
        client, "/news", "News Item", ["lead.png"], title="Our new office", publish="publish"
    )
print(json.dumps(result.to_dict(), indent=2))
```

```json
{
  "operation": "create_with_files",
  "dry_run": false,
  "item": {
    "@id": "http://localhost:8080/Plone/news/our-new-office",
    "@type": "News Item",
    "UID": "e5d8229c6f034218b0e2d99e9bdab722",
    "id": "our-new-office",
    "title": "Our new office",
    "review_state": "published"
  },
  "created": [
    {
      "@id": "http://localhost:8080/Plone/news/our-new-office",
      "@type": "News Item",
      "UID": "e5d8229c6f034218b0e2d99e9bdab722",
      "id": "our-new-office",
      "title": "Our new office",
      "review_state": "private"
    },
    {
      "@id": "http://localhost:8080/Plone/news/our-new-office/lead.png",
      "@type": "Image",
      "UID": "83ca2ca5c3304e20854000772a4e33ee",
      "id": "lead.png",
      "title": "lead.png",
      "review_state": null,
      "source": "lead.png"
    }
  ],
  "changed": [
    {
      "@id": "http://localhost:8080/Plone/news/our-new-office",
      "fields": {
        "preview_image_link": "http://localhost:8080/Plone/news/our-new-office/lead.png"
      }
    },
    {
      "@id": "http://localhost:8080/Plone/news/our-new-office",
      "transition": "publish"
    }
  ],
  "requests": [
    {
      "method": "GET",
      "url": "http://localhost:8080/Plone/++api++/@types/News%20Item",
      "status": 200
    },
    {
      "method": "POST",
      "url": "http://localhost:8080/Plone/++api++/news",
      "status": 201
    },
    {
      "method": "POST",
      "url": "http://localhost:8080/Plone/++api++/news/our-new-office",
      "status": 201
    },
    {
      "method": "PATCH",
      "url": "http://localhost:8080/Plone/++api++/news/our-new-office",
      "status": 204
    },
    {
      "method": "POST",
      "url": "http://localhost:8080/Plone/++api++/news/our-new-office/@workflow/publish",
      "status": 200
    },
    {
      "method": "GET",
      "url": "http://localhost:8080/Plone/++api++/news/our-new-office?include_items=false",
      "status": 200
    }
  ]
}
```

## Dry run

With a client in a {term}`dry run`, the requests that change the site are recorded and skipped, and created entries have `"planned": true` with the path the item would most likely get.
Steps that need an answer from the site, such as the final `GET` and the counts after a copy, are left out.

```python
from plone_client import operations
from plone_client import PloneClient
from pathlib import Path
from seed import png

import json


Path("lead.png").write_bytes(png(0, 90, 0))
url = "http://localhost:8080/Plone"
with PloneClient(url, username="admin", password="admin", dry_run=True) as client:
    result = operations.create_with_files(
        client, "/news", "News Item", ["lead.png"], title="Our new office", publish="publish"
    )
print(json.dumps(result.to_dict(), indent=2))
```

```json
{
  "operation": "create_with_files",
  "dry_run": true,
  "item": {
    "@id": "http://localhost:8080/Plone/news/our-new-office",
    "@type": "News Item",
    "id": "our-new-office",
    "title": "Our new office",
    "planned": true
  },
  "created": [
    {
      "@id": "http://localhost:8080/Plone/news/our-new-office",
      "@type": "News Item",
      "id": "our-new-office",
      "title": "Our new office",
      "planned": true
    },
    {
      "@id": "http://localhost:8080/Plone/news/our-new-office/lead.png",
      "@type": "Image",
      "id": "lead.png",
      "title": "lead.png",
      "planned": true,
      "source": "lead.png"
    }
  ],
  "changed": [
    {
      "@id": "http://localhost:8080/Plone/news/our-new-office",
      "fields": {
        "preview_image_link": "http://localhost:8080/Plone/news/our-new-office/lead.png"
      }
    },
    {
      "@id": "http://localhost:8080/Plone/news/our-new-office",
      "transition": "publish"
    }
  ],
  "requests": [
    {
      "method": "GET",
      "url": "http://localhost:8080/Plone/++api++/@types/News%20Item",
      "status": 200
    },
    {
      "method": "POST",
      "url": "http://localhost:8080/Plone/++api++/news",
      "status": null,
      "dry_run": true
    },
    {
      "method": "GET",
      "url": "http://localhost:8080/Plone/++api++/news/@types",
      "status": 200
    },
    {
      "method": "GET",
      "url": "http://localhost:8080/Plone/++api++/@types/News%20Item",
      "status": 200
    },
    {
      "method": "POST",
      "url": "http://localhost:8080/Plone/++api++/news/our-new-office",
      "status": null,
      "dry_run": true
    },
    {
      "method": "GET",
      "url": "http://localhost:8080/Plone/++api++/news/our-new-office/@types",
      "status": 200
    },
    {
      "method": "GET",
      "url": "http://localhost:8080/Plone/++api++/@types/Image",
      "status": 200
    },
    {
      "method": "PATCH",
      "url": "http://localhost:8080/Plone/++api++/news/our-new-office",
      "status": null,
      "dry_run": true
    },
    {
      "method": "POST",
      "url": "http://localhost:8080/Plone/++api++/news/our-new-office/@workflow/publish",
      "status": null,
      "dry_run": true
    }
  ]
}
```

## Failure

When a request fails part way, the operation raises {class}`~plone_client.exceptions.PloneOperationError`.
Its `result` lists what was already done, and `error` says what stopped it.

```python
from plone_client import operations
from plone_client import PloneClient
from plone_client import PloneOperationError
from pathlib import Path
from seed import png

import json


Path("lead.png").write_bytes(png(0, 90, 0))
with PloneClient("http://localhost:8080/Plone", username="admin", password="admin") as client:
    try:
        operations.create_with_files(
            client, "/news", "News Item", ["lead.png"], title="Broken", publish="no-such-step"
        )
    except PloneOperationError as error:
        print([entry["@id"] for entry in error.result.created])
        print(json.dumps(error.result.error, indent=2))
```

```text
['http://localhost:8080/Plone/news/broken', 'http://localhost:8080/Plone/news/broken/lead.png']
{
  "status_code": 400,
  "type": "WorkflowException",
  "message": "No workflow provides the '${action_id}' action.",
  "method": "POST",
  "url": "http://localhost:8080/Plone/++api++/news/broken/@workflow/no-such-step"
}
```

A problem with the local input raises {class}`ValueError` before anything is sent: a missing file, or a lead image that is not an image.

<!-- check: stop -->

## Module

```{eval-rst}
.. automodule:: plone_client.operations
```

## Related

- {ref}`howto-operations` shows how to use the operations.
- {ref}`reference-assistant-server` offers them as tools.
- {ref}`howto-preview-changes` covers dry runs.
