# Replace a hand-written client

Many projects start with a small `requests` wrapper around plone.restapi: a `from_env()` that reads `REMOTE_URL`, `REMOTE_USER` and `REMOTE_PASSWORD`, a `get`, a `post` and a `patch`.
This guide maps that pattern onto plone-client.

## Create the client

```python
# Before
site = Site.from_env()          # REMOTE_URL, REMOTE_USER, REMOTE_PASSWORD

# After
from plone_client import PloneClient

site = PloneClient.from_env(prefix="REMOTE_")
```

With a prefix, `from_env()` reads `<prefix>USERNAME` and falls back to `<prefix>USER`, so the existing `.env` files keep working.

## Calls

| Hand-written client | plone-client |
|---|---|
| `site.get(path, **params)` | `site.get(path, **params)`, or `site.content.get(path)` |
| `site.post(path, data)` | `site.post(path, data)`, or `site.content.create(path, type, data)` |
| `site.patch(path, data)` | `site.patch(path, data)`, or `site.content.update(path, data)` |
| `site.post(f"{path}/@workflow/publish", {...})` | `site.workflow.transition(path, "publish", effective=...)` |
| `site.get("/@search", UID=uid)` | `site.content.find_by_uid(uid)` |
| a loop over `batching.next` | `site.search.iter(...)` or `site.iter_items(path, params)` |
| `site.path(url)` | `site.path(url)` |
| `requests.HTTPError` | {class}`~plone_client.exceptions.PloneAPIError` and its subclasses |
| a `--apply` flag checked before each change | `PloneClient.from_env(prefix="REMOTE_", dry_run=not args.apply)` |

`get`, `post` and `patch` keep the same shape, so a first migration can change only the import and the constructor.
Move to the managers afterwards, one call at a time.

## Things you get for free

- Requests that are safe to repeat are retried on dropped connections and on 429, 502, 503 and 504 answers.
- Errors carry plone.restapi's own error type and message instead of a bare status code.
- `dry_run=True` records changes instead of sending them, which replaces hand-written "would create" messages.
- `blocks.build()`, `blocks.text()` and `blocks.iter_links()` replace hand-built block dictionaries.
- `files.upload()` and `file_data()` replace hand-written base64 encoding.

## Use a profile on workstations

Scripts that read `REMOTE_*` variables keep the password in a `.env` file.
Switch them to a profile, and the password moves into the keyring.

```python
site = PloneClient.from_profile()   # the project's .plone-client.toml, or the current profile
```

Keep `from_env()` for CI, where the secrets arrive as variables.
