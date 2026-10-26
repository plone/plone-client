---
myst:
  html_meta:
    "description": "Move a project from a small requests wrapper around plone.restapi to plone-client."
    "property=og:description": "Move a project from a small requests wrapper around plone.restapi to plone-client."
    "property=og:title": "Replace a hand-written client"
---

(howto-migrate)=

# Replace a hand-written client

This guide shows you how to move a project from its own small `requests` wrapper around `plone.restapi` to plone-client.
Such wrappers usually have a `from_env()` that reads `REMOTE_URL`, `REMOTE_USER`, and `REMOTE_PASSWORD`, plus `get`, `post`, and `patch`.

## Swap the constructor

```python
from plone_client import PloneClient

site = PloneClient.from_env(prefix="REMOTE_")
```

With a prefix, `from_env()` reads `<prefix>USERNAME` and falls back to `<prefix>USER`, so the project's `.env` files keep working.

`get`, `post`, and `patch` take the same arguments as before, so the first step changes only the import and the constructor.

## Move to the managers, one call at a time

| Hand-written client | plone-client |
|---|---|
| `site.get(path, **params)` | `site.content.get(path)` |
| `site.post(path, data)` | `site.content.create(path, portal_type, data)` |
| `site.patch(path, data)` | `site.content.update(path, data)` |
| `site.post(f"{path}/@workflow/publish", {...})` | `site.workflow.transition(path, "publish", effective=...)` |
| `site.get("/@search", UID=uid)` | `site.content.find_by_uid(uid)` |
| A loop over `batching.next` | `site.search.iter(...)` or `site.iter_items(path, params)` |
| `requests.HTTPError` | {class}`~plone_client.exceptions.PloneAPIError` and its subclasses |
| Base64 encoding of a file by hand | {func}`~plone_client.managers.files.file_data` or `site.files.upload()` |
| Block dictionaries built by hand | {mod}`plone_client.blocks` |

## Replace the apply flag

If the scripts check an `--apply` flag before each change, let the client do it.

```python
site = PloneClient.from_env(prefix="REMOTE_", dry_run=not args.apply)
```

## Move the password into the keyring

On a workstation, create a profile and point the project at it, as {ref}`howto-profiles` shows.
Then read the profile instead of the `.env` file.

```python
site = PloneClient.from_profile()
```

Keep `from_env()` for CI jobs, where the secrets arrive as variables.

## Related

- {ref}`howto-preview-changes` covers `dry_run`.
- {ref}`howto-handle-errors` replaces the `requests` exceptions.
