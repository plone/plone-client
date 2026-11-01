---
myst:
  html_meta:
    "description": "Authentication, profiles, credentials, and utility modules of plone-client."
    "property=og:description": "Authentication, profiles, credentials, and utility modules of plone-client."
    "property=og:title": "Other modules"
---

(reference-python-api)=

# Other modules

| Module | Contents |
|---|---|
| {mod}`plone_client.operations` | Tasks that take several requests in the right order; see {ref}`reference-operations`. |
| {mod}`plone_client.blocks` | Build and walk Volto blocks; see {ref}`reference-blocks`. |
| {mod}`plone_client.mcp_server` | The MCP server; needs the `mcp` extra. |
| {mod}`plone_client.auth` | Authentication flows for httpx: basic, JWT, and a static token. |
| {mod}`plone_client.profiles` | Connection profiles and the configuration file. |
| {mod}`plone_client.credentials` | Secrets of profiles: keyring, environment variable, or command. |
| {mod}`plone_client.utils` | UID references and `resolveuid` links. |

## MCP server

```{eval-rst}
.. automodule:: plone_client.mcp_server
   :members: build_server, serve, tool_errors
```

## Authentication

```{eval-rst}
.. automodule:: plone_client.auth
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
