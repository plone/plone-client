---
myst:
  html_meta:
    "description": "Catch and report the errors plone-client raises, in Python and in shell scripts."
    "property=og:description": "Catch and report the errors plone-client raises, in Python and in shell scripts."
    "property=og:title": "Handle errors"
---

(howto-handle-errors)=

# Handle errors

This guide shows you how to react to the errors a site returns, in Python and in shell scripts.

## Catch a specific error

Catch the exception named after the status you expect.

```python
from plone_client import PloneNotFoundError

try:
    item = client.content.get("/news/hello")
except PloneNotFoundError:
    item = client.content.create("/news", "News Item", id="hello", title="Hello")
```

If you only need to know whether an item exists, use {meth}`~plone_client.managers.content.ContentManager.exists` instead.

```python
if not client.content.exists("/news/hello"):
    client.content.create("/news", "News Item", id="hello", title="Hello")
```

## Report what the site said

Every error the site returns carries `plone.restapi`'s own type and message.

```python
from plone_client import PloneAPIError

try:
    client.content.create("/news", "News Item", title="")
except PloneAPIError as error:
    print(error.status_code, error.error_type, error.message)
```

## Catch everything from plone-client

{class}`~plone_client.exceptions.PloneClientError` is the base of every exception, including connection and configuration errors.

```python
from plone_client import PloneClientError

try:
    sync(client)
except PloneClientError as error:
    raise SystemExit(f"Sync failed: {error}") from error
```

## Handle errors in a shell script

The command line exits with a distinct code per kind of error, so a script can branch without parsing messages.

```shell
plone-client get /news/hello -f UID
case $? in
  0) echo "exists" ;;
  5) plone-client create /news "News Item" --id hello --title Hello ;;
  *) exit 1 ;;
esac
```

The error itself is JSON on standard error.

```shell
plone-client get /missing 2> error.json || jq -r .error.message error.json
```

## Related

- {ref}`reference-exceptions` lists every exception and its exit code.
- {ref}`reference-cli` describes the error output.
