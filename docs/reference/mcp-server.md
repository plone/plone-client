---
myst:
  html_meta:
    "description": "The tools of the plone-client MCP server, their arguments, serving several sites, and how read-only and dry run modes change them."
    "property=og:description": "The tools of the plone-client MCP server, their arguments, serving several sites, and how read-only and dry run modes change them."
    "property=og:title": "MCP server"
---

(reference-assistant-server)=

# MCP server

`plone-client mcp` serves one site, or several, to MCP clients over standard input and output.
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
- The `list_sites` tool returns `items`, each with `name`, `url`, `description`, and `read_only`.
- The server's instructions list the sites with their URL, description, and whether they are read-only.
- Each site has its own client, created the first time a tool uses that site. A profile whose secret is missing fails only when a tool uses it.

With one site, from `--site` or otherwise, tools have no `site` argument and there is no `list_sites`.

(reference-assistant-server-tools)=

## Choosing the tools

The model reads the description of every tool the server offers, so a long list costs context in every conversation.
`--tool` offers only the tools named:

```shell
plone-client mcp --profile blog --tool search --tool get_content --tool list_blocks --tool update_block
```

With several sites, `list_sites` is offered too.
A name the server would not offer, such as a misspelled tool, or a tool that changes the site when it is read-only, stops the command with exit code 3 before it connects to any site; the error lists the tools it offers.
The server's instructions are the same whatever the tools, so they may mention tools that are not offered.

(reference-assistant-server-http)=

## Over HTTP

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

## Tools that read

| Tool | Arguments | Returns |
|---|---|---|
| `site_info` | none | URL, `frontend_url`, whether the server is logged in and as whom, `credentials_rejected` (true when a username or token is configured but the site answers as anonymous), `read_only`, `dry_run`, and the Plone version. |
| `get_content` | `path`, `fields`, `expand` | One item, without the items it contains; only the keys in `fields`, when given. |
| `list_blocks` | `path` | `@id` and `blocks`: an outline of the item's blocks, in order, from {func}`~plone_client.blocks.outline`: `id`, `@type`, the start of their `text`, and the `blocks` inside containers. |
| `list_children` | `path`, `portal_type`, `limit` (1–500, default 50) | `items` inside a folder, in the folder's order, and `items_count`. |
| `search` | `path`, `text`, `portal_type`, `review_state`, `depth`, `query`, `sort_on`, `descending`, `limit` (1–500, default 25) | `items` found and `items_count`. `query` holds any other catalog index. |
| `get_navigation` | `path`, `depth` (1–5, default 2) | The navigation tree. |
| `content_types` | `portal_type`, `addable_in` | The content types, or the JSON schema of `portal_type`. |
| `block_types` | `block_id`, `path` | Markdown: the blocks of the site, or the docs, schema, and variations of one block; see {ref}`reference-managers-block-types`. |
| `get_workflow` | `path` | `state` of an item and the `transitions` it can run now, each with `id` and `title`. |
| `get_vocabulary` | `vocabulary`, `path`, `title`, `limit` (1–500, default 50) | Without `vocabulary`, the vocabularies of the site; with it, `items` (`token` and `title`) and `items_total`. |
| `get_translations` | `path` | The translations linked to an item; needs `plone.app.multilingual`. |
| `get_working_copy` | `path` | The working copy of an item, or the item a working copy belongs to; needs `plone.app.iterate`. |
| `call_service` | `method`, `path`, `params`, `body` | `status` and `body` of any `plone.restapi` request. |

`call_service` is offered in every mode, and follows the server's read-only and dry run settings like any other request.

## Tools that change the site

| Tool | Arguments | Does |
|---|---|---|
| `create_content` | `parent`, `portal_type`, `data`, `publish` | Create one item; returns its summary. |
| `update_content` | `path`, `data` | Change fields of an item. |
| `run_transition` | `path`, `transition`, `comment`, `include_children` | Run a workflow transition. |
| `delete_content` | `paths` | Delete items. |
| `create_content_with_files` | `parent`, `portal_type`, `files`, `data`, `lead_image`, `publish` | {func}`~plone_client.operations.create_with_files`; `files` are local paths. |
| `create_page` | `parent`, `source`, `source_format`, `portal_type`, `title`, `description`, `data`, `files`, `lead_image`, `publish` | {func}`~plone_client.operations.create_page`. `portal_type` defaults to `Document` and must have blocks; `content_types` lists the types addable in a folder. Offered only when `collective.html2blocks` is installed. |
| `upload_tree` | `local_path`, `parent`, `convert_pages`, `publish` | {func}`~plone_client.operations.upload_tree`. |
| `copy_content` | `sources`, `target` | {func}`~plone_client.operations.copy_items`. |
| `move_content` | `sources`, `target` | {func}`~plone_client.operations.move_items`. |
| `add_blocks` | `path`, `items`, `after`, `position` | {func}`~plone_client.operations.add_blocks`. |
| `update_block` | `path`, `block_id`, `data`, `replace` | {func}`~plone_client.operations.update_block`. |
| `remove_blocks` | `path`, `block_ids` | {func}`~plone_client.operations.remove_blocks`. |
| `set_blocks` | `path`, `items` | {func}`~plone_client.operations.set_blocks`. |
| `link_translation` | `path`, `translation` | Link an existing item as a translation. |
| `unlink_translation` | `path`, `language` | Remove the link to the translation in `language`; both items stay. |
| `check_out` | `path` | Check out an item into a working copy; returns its `@id`. |
| `check_in` | `path` | Apply a working copy to its item and remove the working copy. |
| `cancel_working_copy` | `path` | Remove a working copy without applying it. |

The tools that run an operation return its {class}`~plone_client.operations.OperationResult` as JSON.
Paths are site paths such as `/news/item`; the `@id` URLs that tools return work too.

### Blocks

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

## Tool annotations

| Annotation | Tools |
|---|---|
| `readOnlyHint` | `list_sites`, and the tools that read, except `call_service`. |
| `destructiveHint: false` | `create_content`, `create_content_with_files`, `create_page`, `upload_tree`, `copy_content`, `add_blocks`, `link_translation`, `check_out`. |
| `destructiveHint`, `idempotentHint` | `update_content`, `update_block`, `set_blocks`. |
| `destructiveHint`, `idempotentHint: false` | `run_transition`, `move_content`, `check_in`, `call_service`: running them twice does not give the same result, so a client should not retry them. |
| `destructiveHint` | `delete_content`, `remove_blocks`, `unlink_translation`, `cancel_working_copy`. |

(reference-assistant-server-modes)=

## Modes

| Mode | Tools offered | Requests that change the site |
|---|---|---|
| Default | All | Sent. |
| Dry run | All | Recorded and skipped; tools return what would be sent. |
| Read-only | The tools that read | Refused with `PloneReadOnlyError`. |

Read-only applies per site: a site is read-only with `--read-only` or when its profile has `read_only = true`.
The tools that change a site are offered when at least one site is not read-only.
A tool that would change a read-only site is refused with `PloneReadOnlyError` before any request is sent.

The server's instructions, which MCP clients pass to the model, describe the Volto content model and say which sites are read-only and whether the server is in a dry run.
When the credentials of a site were rejected, the instructions warn about it and name the fix.

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
