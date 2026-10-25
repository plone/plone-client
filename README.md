# plone-client

A Python client for [Plone](https://plone.org) sites via [plone.restapi](https://plonerestapi.readthedocs.io).

Inspired by [python-keycloak](https://github.com/marcospereirampj/python-keycloak) — high-level managers for every API feature, automatic retry, environment-variable configuration, and a clean escape hatch for custom endpoints.

---

## Installation

```bash
pip install plone-client
```

For development:

```bash
git clone https://github.com/yourorg/plone-client
cd plone-client
pip install -e ".[dev]"
```

---

## Quick Start

```python
from plone_client import PloneClient

with PloneClient(
    base_url="https://my.plone.site",
    username="admin",
    password="secret",
) as client:
    # Content CRUD
    doc = client.content.create("/news", "Document", title="Hello World")
    results = client.search.search({"portal_type": "Document"})
    client.content.transition(doc["@id"], "publish")

    # Users & groups
    users = client.users.list()
    client.groups.add_member("Reviewers", "jane")

    # Vocabulary lookup
    keywords = client.site.vocabulary("plone.app.vocabularies.Keywords")
```

---

## Configuration

All settings can be passed as keyword arguments **or** via environment variables.

| Argument         | Environment variable              | Default   |
|------------------|-----------------------------------|-----------|
| `base_url`       | `PLONE_CLIENT_BASE_URL`           | —         |
| `username`       | `PLONE_CLIENT_USERNAME`           | —         |
| `password`       | `PLONE_CLIENT_PASSWORD`           | —         |
| `token`          | `PLONE_CLIENT_TOKEN`              | —         |
| `timeout`        | `PLONE_CLIENT_TIMEOUT`            | `30`      |
| `verify_ssl`     | `PLONE_CLIENT_VERIFY_SSL`         | `true`    |
| `max_retries`    | `PLONE_CLIENT_MAX_RETRIES`        | `3`       |
| `retry_backoff`  | `PLONE_CLIENT_RETRY_BACKOFF`      | `0.5`     |
| `log_level`      | `PLONE_CLIENT_LOG_LEVEL`          | `WARNING` |

### Using a config object

```python
from plone_client import PloneClient, PloneClientConfig

cfg = PloneClientConfig(
    base_url="https://my.plone.site",
    username="editor",
    password="secret",
    max_retries=5,
    retry_backoff=1.0,
    log_level="DEBUG",
)

client = PloneClient(config=cfg)
```

---

## Retry policy

Failed requests are automatically retried with exponential back-off:

```
sleep = retry_backoff * (2 ** attempt)
```

Retries happen on:
- Network timeouts
- TCP connection errors
- HTTP `429`, `500`, `502`, `503`, `504` for **idempotent** methods (`GET`, `DELETE`, …)

Non-idempotent methods (`POST`, `PATCH`, `PUT`) are **not** retried on 5xx to avoid
duplicate mutations.

---

## Logging

The library uses a single named logger (`plone_client`) with a `NullHandler` by default,
so it stays silent unless your application configures logging.

### Quick console setup

```python
import logging
from plone_client import setup_logging

setup_logging(level=logging.DEBUG)
```

### Use your own logger

```python
import logging
from plone_client import set_logger

set_logger(logging.getLogger("myapp"))
```

---

## Available managers

| Attribute             | Covers                                               |
|-----------------------|------------------------------------------------------|
| `client.content`      | CRUD, copy/move, workflow, lock, aliases, ordering   |
| `client.search`       | `@search`, `@querystring-search`, lazy iteration     |
| `client.users`        | `@users`, `@my-information`                          |
| `client.groups`       | `@groups`, member management                         |
| `client.sharing`      | `@sharing` (local roles)                             |
| `client.registry`     | `@registry`                                          |
| `client.controlpanels`| `@controlpanels`                                     |
| `client.addons`       | `@addons` (install / uninstall)                      |
| `client.site`         | `@types`, `@vocabularies`, `@roles`, e-mail, undo    |
| `client.comments`     | `@comments`                                          |
| `client.history`      | `@history` (CMFEditions)                             |
| `client.tiles`        | `@tiles`                                             |

---

## Escape hatch

Need to call a custom service, an add-on endpoint, or anything not yet
covered by the built-in managers?

```python
# Raw request — returns a requests.Response
response = client.request("GET", "/@my-addon-endpoint", params={"foo": "bar"})
data = response.json()

# Convenience shorthands
client.get("/@search")
client.post("/news", json={"@type": "Document", "title": "Breaking News"})
client.patch("/news/breaking-news", json={"description": "Updated"})
client.delete("/news/old-news")

# File upload
with open("report.pdf", "rb") as f:
    client.request("POST", "/documents/@@upload", files={"file": f})
```

---

## Error handling

All exceptions derive from `PloneClientError`:

```python
from plone_client import (
    PloneAuthenticationError,
    PloneNotFoundError,
    PloneForbiddenError,
    PloneConflictError,
    PloneServerError,
    PloneTimeoutError,
    PloneConnectionError,
    PloneAPIError,       # catch-all for unexpected status codes
    PloneClientError,    # base — catches everything above
)

try:
    doc = client.content.get("/secret-page")
except PloneNotFoundError:
    print("page does not exist")
except PloneForbiddenError:
    print("no permission")
except PloneClientError as exc:
    print(f"unexpected error: {exc}")
```

---

## Testing

### Unit tests (no Docker required)

```bash
pytest -m unit
```

### Integration tests (requires Docker)

```bash
pytest -m integration
```

The integration suite uses `pytest-docker` to start `plone/plone-backend:6`
automatically.  Override the image with:

```bash
PLONE_DOCKER_IMAGE=plone/plone-backend:6.1 pytest -m integration
```

---

## Contributing

```bash
pip install -e ".[dev]"
ruff check src tests
mypy src
pytest -m unit
```

---

## License

MIT
