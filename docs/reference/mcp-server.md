---
myst:
  html_meta:
    "description": "The tools of the plone-client MCP server, their arguments, serving several sites, and how read-only and dry run modes change them."
    "property=og:description": "The tools of the plone-client MCP server, their arguments, serving several sites, and how read-only and dry run modes change them."
    "property=og:title": "MCP server"
---

<!-- vale Vale.Terms = NO -->

(reference-mcp-server)=
(reference-assistant-server)=

# MCP server

<!-- vale Vale.Terms = YES -->

`plone-client mcp` serves one site, or several, to {term}`MCP` clients, over standard input and output or over HTTP.
It needs the `mcp` extra, which adds the official MCP Python SDK.

## Command

<!-- source: src/plone_client/cli/mcp.py, src/plone_client/mcp_server.py -->

```shell
plone-client mcp --profile blog
plone-client mcp --site blog --site docs
plone-client mcp --group customer
plone-client mcp --all
```

Without `--site`, `--group`, or `--all`, the server serves one site, and takes its connection from the same places as every other command: `--profile`, `$PLONE_CLIENT_PROFILE`, `.plone-client.toml`, the current profile, or `--url` with the `PLONE_CLIENT_*` variables.

| Option | Effect |
|---|---|
| `--site NAME` | Serve the profile `NAME`. Repeat it for several sites. |
| `--group NAME` | Serve the profiles of the group `NAME`; see {ref}`reference-configuration-groups`. Repeatable. |
| `--all` | Serve every profile. |
| `--read-only`, or a profile with `read_only = true` | Refuse changes; see {ref}`reference-assistant-server-modes`. |
| `-n`, `--dry-run` | Tools that change a site return the requests they would send, and send none. |
| `--tool NAME` | Offer only the tool `NAME`. Repeat it for several; see {ref}`reference-assistant-server-tools`. |
| `--http` | Serve over streamable HTTP instead of standard input and output; see {ref}`reference-assistant-server-http`. |
| `--host HOST` | Address to listen on, with `--http`. Default `127.0.0.1`. |
| `--port PORT` | Port to listen on, with `--http`. Default `8000`. |
| `-v`, `--verbose` | Log each request to standard error. |

`--site`, `--group`, and `--all` combine, and each profile is served once: every profile for `--all`, then the `--site` profiles, then the profiles of each group.
They cannot be combined with `--profile` or `--url`; the command exits with code 3.
`--read-only`, `--dry-run`, and `--verbose` apply to every site.
`--read-only` must come before `mcp`.
Without the `mcp` extra, the command exits with code 3.

(reference-assistant-server-sites)=

## Several sites

With more than one site, the server changes as follows.

- Every tool has a required `site` argument, listed first, whose values are the profile names.
- The `list_sites` tool returns `items`, each with `name`, `url`, `description`, `read_only`, and `blocks`.
- The server's instructions list the sites with their URL, description, and whether they are read-only.
- Each site has its own client, created the first time a tool uses that site. A profile whose secret is missing fails only when a tool uses it.

With one site, from `--site` or otherwise, tools have no `site` argument and there is no `list_sites`.

(reference-assistant-server-tools)=

## Choosing the tools

```{versionadded} 1.0.0a2
```

The model reads the description of every tool the server offers, so a long list costs context in every conversation.
`--tool` offers only the tools named:

```shell
plone-client mcp --profile blog --tool search --tool get_content --tool list_blocks --tool update_block
```

With several sites, `list_sites` is offered too.
{ref}`howto-protect` recommends sets of tools.

(reference-assistant-server-resources)=

## Resources

```{versionadded} 1.0.0a3
```

Each site also has read-only resources: data that you, or the application you use, can attach to a conversation.
The model calls tools by itself, while how resources are used depends on the application, so they add to the tools and do not replace them.

```{include} ../_generated/mcp-resources.md
```

`get_content` decides whether `site` and `content` are offered, `content_types` decides for `types`, and `block_types` decides for `blocks`.

`<site>` is the name of the profile, percent-encoded, and `site` for a server that was built from a client rather than from profiles.
With `--tool`, a resource is offered only when the tool in the table is, so resources do not widen the access that you chose.
A path with `..` in it is refused, and so is a resource of a site that the server does not have.
Resources wait for the same per-site turn as tools.
A name the server would not offer, such as a misspelled tool, or a tool that changes the site when it is read-only, stops the command with exit code 3 before it connects to any site; the error lists the tools it offers.
The server's instructions are the same whatever the tools, so they may mention tools that are not offered.

(reference-assistant-server-http)=

## Over HTTP

```{versionadded} 1.0.0a2
```

<!-- source: src/plone_client/mcp_server.py, src/plone_client/credentials.py, src/plone_client/cli/mcp.py -->

With `--http`, the server speaks streamable HTTP at `http://HOST:PORT/mcp`, for assistants that do not start a local command.
The tools, the sites, and the modes are the same as over standard input and output.

Every request needs the header `Authorization: Bearer TOKEN`, loopback included; without it, or with another token, the server answers `401`.
The token is compared in constant time.
`plone-client mcp --http` reads it from `$PLONE_CLIENT_MCP_TOKEN`, or else from the keyring, and stops with exit code 3 before connecting to any site when there is none, or when it is shorter than 32 characters.

| Command | Does |
|---|---|
| `plone-client mcp-token generate` | Makes a random token, stores it in the keyring, and prints it as `token`. A token stored before is replaced. |
| `plone-client mcp-token set` | Stores a token of your own, from a hidden prompt or, with `--token-stdin`, from standard input. |
| `plone-client mcp-token delete` | Removes the token from the keyring; prints `deleted`. |

On `127.0.0.1`, `localhost`, and `::1`, the server also refuses requests whose `Host` header names another host (`421`), which protects against DNS rebinding.
On other addresses, put the server behind a proxy that adds TLS: the token, and the content of the site, would otherwise cross the network in clear text.

The site's own credentials stay in the server's profiles.
A client of the HTTP server never sees them, and cannot point the server at another site.
One server answers every client that has the token, with the same profiles: give each person or team their own server and token when they should not share access.

Tools run one at a time per site, so that operations and block edits from several clients do not mix.

The server writes the address it listens on to standard error, and stops on `Ctrl+C` or `SIGTERM`.

(reference-assistant-server-tool-list)=

## Tools

```{include} ../_generated/mcp-tools.md
```

A `?` marks an optional argument.
With several sites, every tool but `list_sites` also takes a required `site`.
The column *Effect* comes from the tool's annotations: `reads`, `adds` (`destructiveHint: false`), `changes` (`destructiveHint`), and `changes, repeatable` (`destructiveHint`, `idempotentHint`).
A client should not retry a tool that is only `changes`: running it twice does not give the same result.

`create_page` is offered only when `collective.html2blocks` is installed.
`get_translations` needs `plone.app.multilingual`, and `get_working_copy` needs `plone.app.iterate`.
`create_content_with_files`, `create_page`, and `upload_tree` read local paths on the computer of the server.

`call_service` is offered in every mode, and follows the server's read-only and dry run settings like any other request.

The `blocks` argument of `create_page` and `upload_tree` chooses the block types that Markdown and HTML become, merged over the `blocks` setting of the site's profile; see {ref}`reference-configuration-blocks`.
When a site has such a setting, the server's instructions state it.

The tools that run an operation return its {class}`~plone_client.operations.OperationResult` as JSON.
Paths are site paths such as `/news/item`; the `@id` URLs that tools return work too.

### Blocks

```{versionadded} 1.0.0a2
```

The tools that take blocks take them as a list, in order, each with an `@type`.
The server gives them ids and builds the layout, and goes through {func}`~plone_client.blocks.normalize`: a string `href` becomes a list of links, and a container such as a `gridBlock` can list its own `blocks` the same way.

```json
[
  {"@type": "slate", "plaintext": "Latest news"},
  {
    "@type": "gridBlock",
    "blocks": [
      {"@type": "teaser", "href": "/news/first"},
      {"@type": "teaser", "href": "/news/second"}
    ]
  }
]
```

`create_content` and `update_content` accept such a list as `data["blocks"]` too, through {func}`~plone_client.blocks.prepare`.
A mapping of block ids also works; its layout is then tidied with {func}`~plone_client.blocks.tidy`.
A block without `@type` is refused with `ValueError` before any request is sent.

`add_blocks`, `update_block`, `remove_blocks`, and `set_blocks` read the item, change its blocks, and save them with one `PATCH`.
They work on blocks inside containers too, and return an outline of the saved blocks in `item.blocks`.
They take no lock, so a change someone else saves between the read and the write is lost.

(reference-assistant-server-modes)=

## Modes

| Mode | Tools offered | Requests that change the site |
|---|---|---|
| Default | All | Sent. |
| Dry run | All | Recorded and skipped; tools return what would be sent. |
| Read-only | The tools that read | Refused with `PloneReadOnlyError`. |

Read-only applies per site: a site is read-only with `--read-only` or when its profile has `read_only = true`.
The tools that change a site are offered when at least one site is not read-only.
A tool that would change a read-only site is refused with `PloneReadOnlyError` before any change is sent; it can read from the site first.

The server's {term}`instructions`, which MCP clients pass to the model, describe the Volto content model and say which sites are read-only and whether the server is in a dry run.
When the credentials of a site were rejected, the instructions warn about it and name the fix.

````{dropdown} The instructions of every server
```{include} ../_generated/mcp-instructions.md
```
````

### Rejected credentials

Plone answers a wrong password as an anonymous request, so reads still work and only changes fail.
When a site is configured with a username or token and answers as anonymous, `plone-client mcp` checks each site at startup and writes a warning to standard error: the server still starts.
The same warning is in the instructions, and `site_info` reports `credentials_rejected`.
A site with no username or token that answers as anonymous is not reported.
Fix the secret with `plone-client profile set-secret NAME`.

## Errors

A tool that fails returns an error result whose text is the same JSON the command line prints on standard error: `error` with `type`, `message`, and, for errors answered by the site, `status_code`, `method`, and `url`.
An operation that stops part way also returns `result`, with what it had done.
`ValueError` and `OSError`, such as a missing local file, return `error` with their type and message.

## Related

- {ref}`howto-assistant` connects an assistant to a site.
- {ref}`explanation-interfaces` compares the MCP server, the command line, and the agent skill.
- {ref}`reference-operations` lists the requests of each operation.
- {ref}`howto-protect` chooses a mode and a short list of tools.
