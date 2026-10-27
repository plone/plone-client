---
myst:
  html_meta:
    "description": "Authentication, blocks, profiles, credentials, and utility modules of plone-client."
    "property=og:description": "Authentication, blocks, profiles, credentials, and utility modules of plone-client."
    "property=og:title": "Other modules"
---

(reference-python-api)=

# Other modules

| Module | Contents |
|---|---|
| {mod}`plone_client.operations` | Tasks that take several requests in the right order, with a result that lists every request. |
| {mod}`plone_client.mcp_server` | The MCP server; needs the `mcp` extra. |
| {mod}`plone_client.auth` | Authentication flows for httpx: basic, JWT, and a static token. |
| {mod}`plone_client.blocks` | Build Volto blocks, including blocks of any type and blocks that hold others, such as grids; convert Markdown and HTML to blocks; and walk blocks and their links. |
| {mod}`plone_client.profiles` | Connection profiles and the configuration file. |
| {mod}`plone_client.credentials` | Secrets of profiles: keyring, environment variable, or command. |
| {mod}`plone_client.utils` | UID references and `resolveuid` links. |

(reference-operations)=

## Operations

| Function | Requests, in order |
|---|---|
| {func}`~plone_client.operations.create_with_files` | `GET @types/<type>`, create the item, one upload per file, `PATCH preview_image_link` when the type keeps its lead image there, the transition, and `GET` of the item. |
| {func}`~plone_client.operations.create_page` | Create the page, then the transition and `GET` of the page. |
| {func}`~plone_client.operations.upload_tree` | `GET` of the folder, then one create or upload per entry, depth first, and a transition after each new page. |
| {func}`~plone_client.operations.copy_items`, {func}`~plone_client.operations.move_items` | `GET` of the folder, a `@search` count per item, `@copy` or `@move`, and a `@search` count per new item. |

Transitions run only when `publish` is given.
With a `dry_run` client, the requests that change the site are recorded and skipped, and created entries have `"planned": true` with the path the item would most likely get.
Steps that need an answer from the site, such as the final `GET` and the counts after a copy, are left out.

```{eval-rst}
.. automodule:: plone_client.operations
```

## MCP server

```{eval-rst}
.. automodule:: plone_client.mcp_server
   :members: build_server, serve, tool_errors
```

## Authentication

```{eval-rst}
.. automodule:: plone_client.auth
```

## Blocks

```{eval-rst}
.. automodule:: plone_client.blocks
```

## Profiles

```{eval-rst}
.. automodule:: plone_client.profiles
```

## Credentials

```{eval-rst}
.. automodule:: plone_client.credentials
```

## Utilities

```{eval-rst}
.. automodule:: plone_client.utils
```

## Related

- {ref}`reference-client` documents the client itself.
- {ref}`reference-configuration` describes the configuration file.
