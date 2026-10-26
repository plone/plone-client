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

## Preview the changes of a script

Create the client with `dry_run=True`.
Reads still go to the site, so the script behaves as usual, but each changing request is recorded in `client.dry_run_log` instead of being sent.

```python
client = PloneClient.from_env(dry_run=True)
client.content.update("/news/hello", title="Hello, Plone")

for request in client.dry_run_log:
    print(request["method"], request["url"], request.get("json"))
```

Each skipped call returns the record of the request instead of the site's answer.
A create therefore returns no `@id`; stop before any step that needs one.

A common pattern is to plan by default and change the site only when asked.

```python
client = PloneClient.from_env(dry_run=not args.apply)
```

## Preview the changes of a command

Pass `-n` anywhere on the command line.
The command prints the requests it would send, and sends none of them.

```shell
plone-client -n delete /news/hello
plone-client update /news/hello --title "Hello, Plone" -n
```

With `-n`, destructive commands do not ask for confirmation.

## Refuse every change

Create the client with `read_only=True`.
Any request that could change the site raises {class}`~plone_client.exceptions.PloneReadOnlyError` before it is sent.

```python
client = PloneClient.from_profile("production", read_only=True)
```

On the command line, pass `--read-only` before the command, or create the profile with `--read-only` so it always refuses changes.

```shell
plone-client --read-only -p production ls /news
plone-client profile add production --url https://example.org --username editor --read-only
```

Searches through `@querystring-search` and logins still work, because those services answer a `POST` without changing anything.

## Related

- {ref}`reference-client` lists exactly what each switch allows.
- {ref}`howto-agents` combines both switches for coding agents.
