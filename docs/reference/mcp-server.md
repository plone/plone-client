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

## Tools that read

| Tool | Arguments | Returns |
|---|---|---|
| `site_info` | none | URL, `frontend_url`, whether the server is logged in and as whom, `credentials_rejected` (true when a username or token is configured but the site answers as anonymous), `read_only`, `dry_run`, and the Plone version. |
| `get_content` | `path`, `fields`, `expand` | One item, without the items it contains; only the keys in `fields`, when given. |
| `list_children` | `path`, `portal_type`, `limit` (1–500, default 50) | `items` inside a folder, in the folder's order, and `items_count`. |
| `search` | `path`, `text`, `portal_type`, `review_state`, `depth`, `query`, `sort_on`, `descending`, `limit` (1–500, default 25) | `items` found and `items_count`. `query` holds any other catalog index. |
| `get_navigation` | `path`, `depth` (1–5, default 2) | The navigation tree. |
| `content_types` | `portal_type`, `addable_in` | The content types, or the JSON schema of `portal_type`. |
| `block_types` | `block_id`, `path` | Markdown: the blocks of the site, or the docs, schema, and variations of one block; see {ref}`reference-managers-block-types`. |
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

The tools that run an operation return its {class}`~plone_client.operations.OperationResult` as JSON.
Paths are site paths such as `/news/item`; the `@id` URLs that tools return work too.

## Tool annotations

| Annotation | Tools |
|---|---|
| `readOnlyHint` | `list_sites`, and the tools that read, except `call_service`. |
| `destructiveHint: false` | `create_content`, `create_content_with_files`, `create_page`, `upload_tree`, `copy_content`. |
| `destructiveHint`, `idempotentHint` | `update_content`, `run_transition`, `move_content`, `call_service`. |
| `destructiveHint` | `delete_content`. |

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
