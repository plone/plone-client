---
myst:
  html_meta:
    "description": "Preview the changes a script or command would make to a Plone site, or make a client refuse every change."
    "property=og:description": "Preview the changes a script or command would make to a Plone site, or make a client refuse every change."
    "property=og:title": "Preview changes and protect a site"
---

(howto-preview-changes)=

# Preview changes and protect a site

This guide shows you how to see what a script or command would change before it changes anything, and how to make a client unable to change a site at all.

The examples run against the {term}`Compose site`; see {ref}`howto-run-a-site`.
Point the command line and your scripts at it.

<!-- check: start -->

```shell
export PLONE_CLIENT_URL=http://localhost:8080/Plone
export PLONE_CLIENT_USERNAME=admin
export PLONE_CLIENT_PASSWORD=admin
```

## Choose between a dry run and read-only

| | {term}`Dry run` | {term}`Read-only` |
|---|---|---|
| In Python | `dry_run=True` | `read_only=True` |
| On the command line | `-n`, anywhere on the line | `--read-only`, before the command |
| In a {term}`profile` | Not available. | `--read-only` when you add it. |
| Reads | Sent. | Sent. |
| Changes | Skipped, and printed. | Refused. |
| What a command reports | The request it would send, with exit code 0. | An error, with exit code 7. |
| What a script gets | The record of the request, in place of the answer. | {class}`~plone_client.exceptions.PloneReadOnlyError` |
| Use it to | See what would happen. | Make sure that nothing can happen. |

With both, read-only wins: `-n` on a read-only {term}`profile` is refused with exit code 7, so a read-only site cannot preview a change.

The same change, with each switch:

```shell
plone-client -n update /news/release-party --title "Party in Brasília"
```

```json
{
  "dry_run": true,
  "method": "PATCH",
  "url": "http://localhost:8080/Plone/++api++/news/release-party",
  "json": {
    "title": "Party in Brasília"
  }
}
```

<!-- check: exit 7 -->
```shell
plone-client --read-only update /news/release-party --title "Party in Brasília"
```

```json
{
  "error": {
    "type": "PloneReadOnlyError",
    "message": "PATCH /news/release-party refused: the client is read-only"
  }
}
```

## Preview the changes of a script

Create the client with `dry_run=True`.
Reads still go to the site, so the script behaves as usual, but each changing request is recorded in `client.dry_run_log` instead of being sent.

<!-- check: file preview.py -->
```python
from plone_client import PloneClient

client = PloneClient.from_env(dry_run=True)
client.content.update("/news/release-party", title="Party in Brasília")

for request in client.dry_run_log:
    print(request["method"], request["url"], request.get("json"))
```

```shell
python preview.py
```

```text
PATCH http://localhost:8080/Plone/++api++/news/release-party {'title': 'Party in Brasília'}
```

Each skipped call returns the record of the request instead of the site's answer.
A create therefore returns no `@id`; stop before any step that needs one.

A common pattern is to plan by default and change the site only when asked.

<!-- check: skip -->
```python
client = PloneClient.from_env(dry_run=not args.apply)
```

## Preview the changes of a command

Pass `-n` anywhere on the command line.
The command prints the requests it would send, and sends none of them.

```shell
plone-client -n delete /news/release-party
plone-client update /news/release-party --description "Join us" -n
```

```text
{
  "deleted": [
    "/news/release-party"
  ],
  "dry_run": true
}
{
  "dry_run": true,
  "method": "PATCH",
  "url": "http://localhost:8080/Plone/++api++/news/release-party",
  "json": {
    "description": "Join us"
  }
}
```

With `-n`, destructive commands do not ask for {term}`confirmation`.

## Refuse every change

Create the client with `read_only=True`.
Any request that could change the site raises {class}`~plone_client.exceptions.PloneReadOnlyError` before it is sent.

<!-- check: file refuse.py -->
```python
from plone_client import PloneClient
from plone_client.exceptions import PloneReadOnlyError

client = PloneClient.from_env(read_only=True)
try:
    client.content.delete("/news/release-party")
except PloneReadOnlyError as error:
    print(error)
```

```shell
python refuse.py
```

```text
DELETE /news/release-party refused: the client is read-only
```

On the command line, pass `--read-only` before the command, or create the profile with `--read-only` so it always refuses changes.

<!-- check: skip -->
```shell
plone-client --read-only -p production ls /news
plone-client profile add production --url https://example.org --username editor --read-only
```

Searches through `@querystring-search` and logins still work, because those services answer a `POST` without changing anything.

<!-- check: stop -->

## Related

- {ref}`reference-client` lists exactly what each switch allows.
- {ref}`howto-agents` combines both switches for coding agents.
- {ref}`howto-protect` applies them to assistants.
