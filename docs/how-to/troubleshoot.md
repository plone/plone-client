---
myst:
  html_meta:
    "description": "Find the cause of a problem with plone-client from its symptom, and fix it: connections, credentials, fields, workflow, keyring, and MCP clients."
    "property=og:description": "Find the cause of a problem with plone-client from its symptom, and fix it: connections, credentials, fields, workflow, keyring, and MCP clients."
    "property=og:title": "Troubleshoot"
---

(howto-troubleshoot)=

# Troubleshoot

This guide takes you from a symptom to its cause and its fix.
Each entry says which interfaces it applies to.
The examples use the {term}`Compose site`; see {ref}`howto-run-a-site`.

<!-- check: start -->
```shell
export PLONE_CLIENT_PASSWORD=admin
```

## The site cannot be reached

Applies to the library, the command line, and the MCP server.

<!-- check: exit 8 -->
```shell
plone-client --url http://localhost:9 -u admin info
```

```text
{
  "error": {
    "type": "PloneConnectionError",
    "message": "GET http://localhost:9/++api++/@actions?categories%3Alist=user: [Errno 61] Connection refused"
  }
}
```

The address is wrong, or the site is down.
The exception is {class}`~plone_client.exceptions.PloneConnectionError`, and the exit code is 8.
Open the URL in a browser, and check the port and the site id.
A backend without a frontend has the site id in its URL, as in `http://localhost:8080/Plone`.

## The site answers as if you had not logged in

Applies to the library, the command line, and the MCP server.

Plone answers a wrong password as an anonymous request, so reads of public content still work, and only changes fail.

<!-- check: exit 4 -->
```shell
PLONE_CLIENT_PASSWORD=wrong plone-client --url http://localhost:8080/Plone -u admin info -f authenticated,credentials_rejected
```

```json
{
  "authenticated": false,
  "credentials_rejected": true
}
```

`credentials_rejected` says that the site refused the {term}`secret`, and `info` exits with code 4.
Fix it with `plone-client profile set-secret NAME`, and see {ref}`howto-profiles`.

## Lists and items come back empty

Applies to the library, the command line, and the MCP server.

An address that ends in {term}`++api++` is not an error: the requests work, and their answers are empty.

```shell
plone-client --url http://localhost:8080/Plone/++api++ -u admin get /news -c
```

```json
{"context": "http://localhost:8080/Plone", "message": "http://localhost:8080/Plone/++api++/news", "type": "Redirect"}
```

Give plone-client the address of the site, because it adds that segment by itself.
The address of a {term}`Compose site` is `http://localhost:8080/Plone`.

## Requests end in a server error about `portal_catalog`

Applies to the library, the command line, and the MCP server.

The address has no site id, so the request reaches the server and not the site.

<!-- check: exit 9 -->
```shell
plone-client --url http://localhost:8080 -u admin ls /
```

```text
{
  "error": {
    "status_code": 500,
    "type": "AttributeError",
    "message": "portal_catalog",
    "method": "GET",
    "url": "http://localhost:8080/++api++/@search?path.depth=1&sort_on=getObjPositionInParent&b_size=100"
  }
}
```

Add the id of the site to the address, as in `http://localhost:8080/Plone`.

## A change is refused with 401 or 403

Applies to the library, the command line, and the MCP server.

Exit code 4 covers two causes: the user lacks the permission, or someone holds a lock on the item.
A missing permission answers `401`, even to a user who is logged in.

<!-- check: exit 4 -->
```shell
PLONE_CLIENT_PASSWORD=correct-horse-battery plone-client --url http://localhost:8080/Plone -u jdoe registry set plone.site_title '"New title"'
```

```text
{
  "error": {
    "status_code": 401,
    "type": "Unauthorized",
    "message": "You are not authorized to access this resource.",
    "method": "PATCH",
    "url": "http://localhost:8080/Plone/++api++/@registry"
  }
}
```

Give the user a role that has the permission, or use another user; see {ref}`howto-users-sharing`.
A lock answers `403`.

```shell
plone-client --url http://localhost:8080/Plone -u admin request POST /about/@lock -d '{}' -f locked,creator
```

```json
{
  "locked": true,
  "creator": "admin"
}
```

<!-- check: exit 4 -->
```shell
PLONE_CLIENT_PASSWORD=correct-horse-battery plone-client --url http://localhost:8080/Plone -u jdoe update /about --title "New title"
```

```text
{
  "error": {
    "status_code": 403,
    "type": "Forbidden",
    "message": "Resource is locked.",
    "method": "PATCH",
    "url": "http://localhost:8080/Plone/++api++/about"
  }
}
```

Read `lock` in `plone-client get /about -f lock` to see who holds it.
A lock ends by itself after its `timeout`, or when its owner removes it.

```shell
plone-client --url http://localhost:8080/Plone -u admin request DELETE /about/@lock -f locked
```

```json
{
  "locked": false
}
```

## A field does not change, and there is no error

Applies to the library, the command line, and the MCP server.

Plone ignores the fields that a {term}`content type` does not have, so a misspelled field gets no error and no effect.

```shell
plone-client --url http://localhost:8080/Plone -u admin update /about -s titel=Oops -f title
```

```json
{
  "title": "About"
}
```

List the fields of the type before you set them.

```shell
plone-client --url http://localhost:8080/Plone -u admin types Document -f title,required
```

```json
{
  "title": "Page",
  "required": [
    "title"
  ]
}
```

## A transition is refused

Applies to the library, the command line, and the MCP server.

Each {term}`workflow` state has its own {term}`transitions <transition>`: a published item cannot be submitted.

<!-- check: exit 6 -->
```shell
plone-client --url http://localhost:8080/Plone -u admin workflow /about submit
```

```text
{
  "error": {
    "status_code": 400,
    "type": "WorkflowException",
    "message": "No workflow provides the '${action_id}' action.",
    "method": "POST",
    "url": "http://localhost:8080/Plone/++api++/about/@workflow/submit"
  }
}
```

The message is the raw one of Plone, with its unfilled `${action_id}`.
Ask which transitions the item has now.

```shell
plone-client --url http://localhost:8080/Plone -u admin workflow /about -f state,transitions
```

```json
{
  "state": {
    "id": "published",
    "title": "Published"
  },
  "transitions": [
    "reject",
    "retract"
  ]
}
```

## The block types come from `builtin`

Applies to the library, the command line, and the MCP server.

The answer describes only the core blocks when plone-client could not ask {term}`Volto`.

```shell
plone-client --url http://localhost:8080/Plone -u admin block-types -f source,warning
```

```json
{
  "source": "builtin",
  "warning": "http://localhost:8080/Plone has no @blocks-schema service; set frontend_url to the Volto server, or upgrade Volto"
}
```

Set the {term}`frontend_url` of the site, and use Volto 19.6.0 or later.

```shell
PLONE_CLIENT_FRONTEND_URL=http://localhost:3000 PLONE_CLIENT_URL=http://localhost:8080/Plone PLONE_CLIENT_USERNAME=admin plone-client block-types -f source
```

```json
{
  "source": "site"
}
```

<!-- check: stop -->

## A certificate is refused

Applies to the library, the command line, and the MCP server.

A site with a self-signed certificate, or one from a private authority, fails with a connection error.
Set `verify` to the path of the certificate of the authority; see {ref}`reference-configuration`.

## Markdown pages fail with exit code 3

Applies to the library, the command line, and the MCP server.

`create-page` and `upload-tree --pages` need the `markdown` extra, which needs Python 3.12 or later.
On Python 3.11 the extra installs nothing, so the error remains.
Install the extra as {ref}`howto-install` shows, on Python 3.12 or later.

## The keyring is not available

Applies to the command line and the MCP server.

A container or a CI job often has no {term}`keyring`, and `profile add` ends with this error, and exit code 1.

```text
keyring.errors.NoKeyringError: No recommended backend was available.
```

Keep the secret in an environment variable; see {ref}`howto-scripts-ci`.

## A request ends in 409

Applies to the library, the command line, and the MCP server.

The request conflicts with the state of the site, such as a change that someone else saved first.
The exception is {class}`~plone_client.exceptions.PloneConflictError`, and the exit code is 6.
Read the item again, and repeat the change.

## Requests get slow, or end in 429

Applies to the library, the command line, and the MCP server.

The client repeats idempotent requests after `429`, `502`, `503`, and `504`, and waits as long as `Retry-After` says.
A `POST` is never repeated, so it fails on the first of these answers.
Lower your rate, or set `retries` and `backoff`; see {ref}`reference-configuration`.

## The MCP server does not start

Applies to the MCP server.

Exit code 3 means that the `mcp` extra is missing, or that the {term}`profile` is unknown; the error says which.
Install the extra as {ref}`howto-install` shows, and run the command that your MCP client runs, in a terminal, to read the error.

## An MCP client does not show a tool

Applies to the MCP server.

`--tool` offers only the tools you name, and a server of a {term}`read-only` site does not offer the tools that change it.
{ref}`reference-assistant-server` says which tools each mode offers.

## An HTTP client gets 401 or 421

Applies to the MCP server over HTTP.

`401` means that the bearer token is missing or wrong, and `421` means that the `Host` header is not one the server accepts.
{ref}`howto-assistant` shows how to set both.

## The demo site shows something else

Applies to everything that uses `demo.plone.org`.

The {term}`demo site` is shared with other visitors, and resets every night, so its content does not always match these pages.
Use your own {term}`Compose site` for anything that must stay the same; see {ref}`howto-run-a-site`.

## Related

- {ref}`howto-handle-errors` handles errors in code.
- {ref}`reference-exceptions` lists the exceptions, with their statuses.
- {ref}`reference-cli` lists the exit codes.
