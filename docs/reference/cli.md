---
myst:
  html_meta:
    "description": "Commands, global options, output format, and exit codes of the plone-client command line."
    "property=og:description": "Commands, global options, output format, and exit codes of the plone-client command line."
    "property=og:title": "Command line"
---

(reference-cli)=

# Command line

`plone-client` is installed with the `cli` extra.
Run `plone-client <command> --help` for the options of each command.

## Global options

<!-- source: src/plone_client/cli/app.py, src/plone_client/cli/output.py -->

| Option | Meaning | Anywhere on the line |
|---|---|---|
| `-p`, `--profile <name>` | Profile to use; also `$PLONE_CLIENT_PROFILE`. | Yes |
| `--config <file>` | Configuration file; also `$PLONE_CLIENT_CONFIG`. | Yes |
| `--url <url>` | Site URL, instead of a profile; the password comes from `$PLONE_CLIENT_PASSWORD`. | No |
| `-u`, `--username <name>` | Login name, with `--url`. | No |
| `--read-only` | Refuse any change to the site. | No |
| `-n`, `--dry-run` | Print the changes instead of sending them. | Yes |
| `-f`, `--fields <keys>` | Comma-separated keys to keep in the output. | Yes |
| `-c`, `--compact` | Print JSON on one line. | Yes |
| `-v`, `--verbose` | Log each request to standard error. | Yes |
| `--version` | Print the version. | No |

Options marked "No" must come before the command, because `profile add` has options with the same names.

## Commands

<!-- source: src/plone_client/cli/content.py, src/plone_client/cli/operations.py, src/plone_client/cli/site.py, src/plone_client/cli/mcp.py, src/plone_client/cli/profile.py -->

`plone-client --help` lists the commands in the groups below, and each command group splits its subcommands into **Browse** (read only) and **Write** panels.
In a terminal, the help draws each group as a box.
When the output goes to a pipe or a file, as it does for scripts and coding agents, the help is plain text with the same groups as titled sections.
To get plain help in a terminal too, set `TYPER_USE_RICH=0`.

`<ref>` accepts a path, a URL inside the site, `uid:<UID>`, or a `resolveuid` link.

### Read content

| Command | Does |
|---|---|
| `get <ref>` | Print an item. |
| `ls [ref]` | List the items inside a folder, in order. |
| `search [ref]` | Search the catalog, inside a folder or the whole site. |
| `resolve <ref>` | Print the path, URL, and UID of an item. |
| `blocks <ref>` | Summarize the blocks of an item, nested ones included. |
| `history <ref>` | List the versions and workflow history of an item. |
| `sharing <ref>` | Show the local roles of an item. |

### Change content

| Command | Does |
|---|---|
| `create <parent> <type>` | Create an item inside a folder. |
| `create-page <parent> <file>` | Create a page from Markdown, or HTML with `--html` or an `.html` file, converted to blocks; `-` reads standard input. `--type` picks the content type, which must have blocks; `--file` uploads files inside the page, with `--lead N` and `--no-lead` as for `create-with-files`. Needs the `markdown` extra. |
| `create-with-files <parent> <type> <file>…` | Create an item, upload files and images inside it, and set its lead image; `--lead N` picks the Nth file, `--no-lead` sets none. |
| `update <ref>` | Change fields of an item. |
| `workflow <ref> [transition]` | Show the workflow state and transitions of an item, or run a transition. |
| `copy <ref>… --to <folder>` | Copy items into a folder. |
| `move <ref>… --to <folder>` | Move items into a folder. |
| `order <folder> <id> <delta>` | Move an item within its folder: `top`, `bottom`, `up`, `down`, or a signed number. |
| `delete <ref>…` | Delete items. |

### Files

| Command | Does |
|---|---|
| `upload <parent> <file>…` | Upload files as `File` or `Image` items; `--tus` uploads in chunks. |
| `upload-tree <folder> <parent>` | Upload the contents of a local folder as pages, files, and images, keeping its structure; `--pages` turns Markdown and HTML files into pages. |
| `download <ref>` | Download the file or image of an item. |

### Site users, settings, and types

| Command | Does |
|---|---|
| `types [type]` | List content types, or show the JSON schema of one. |
| `block-types [block]` | List the blocks of the site, or show the docs, schema, and variations of one; `--for <ref>` lists only the blocks that editors can add to an item, and `--markdown` prints Markdown. |
| `vocabulary [name]` | List vocabularies, or the terms of one. |
| `users list`, `get` / `create`, `update`, `delete` | Browse and manage users. |
| `groups list`, `get` / `create`, `delete` / `add-member`, `remove-member` | Browse and manage groups and their members. |
| `registry list`, `get` / `set` | Browse and change registry records. |
| `aliases list` / `add`, `remove` | Browse and manage URL aliases. |

### Advanced

| Command | Does |
|---|---|
| `request <method> <ref>` | Send any request, for services without a command. |
| `mcp` | Serve sites as an MCP server over standard input and output: the selected profile, or several with `--site`, `--group`, and `--all`; see {ref}`reference-assistant-server`. Needs the `mcp` extra. |

`create-page`, `create-with-files`, and `upload-tree` run the operations of {mod}`plone_client.operations` and print their result: `created`, `changed`, and every request in `requests`.
When one of them stops part way, the error on standard error also has a `result` with what was already done, and the exit code is that of the request that failed.

### Connection, profiles, and agents

| Command | Does |
|---|---|
| `info` | Show the profile, site, and user the command line connects with, and the Plone version. If the site rejected the profile's credentials, the output has `credentials_rejected: true` and a `message` that names the fix, and the exit code is 4. |
| `profile list`, `show` / `add`, `use`, `defaults`, `remove` / `set-secret`, `test` | Manage connection profiles; `add` and `defaults` take `--timeout`, `--verify` (`true`, `false`, or a CA bundle path), `--retries`, and `--backoff`. |
| `profile groups` / `group-set NAME PROFILE...`, `group-remove NAME` | List, create or replace, and remove groups of profiles; see {ref}`reference-configuration-groups`. |
| `skill show` / `install` | Print the agent skill, or install it in `.claude/skills`; `--user` installs it in `~/.claude/skills`, `--dir` in another skills directory. |

In the group rows, `/` separates the panels of the group's help: Browse, then Write, then Membership or Connection.

## Field values

`create` and `update` merge field values from these options, each one winning over the previous.

| Order | Option | Value |
|---|---|---|
| 1 | `-d`, `--data` | A JSON object, `@file.json` to read a file, or `-` to read standard input. |
| 2 | `-s`, `--set`, repeatable | `key=text` sets a string; `key:=json` sets any JSON value. |
| 3 | `--title`, `--description` | The title and the description. |

`create` adds a title block and a description block to an item created without `blocks`, unless given `--no-blocks`.

## Output

Results are JSON on standard output, indented unless `-c` is given.
Commands that create or change an item print `@id`, `@type`, `UID`, `id`, `title`, and `review_state`, unless given `--full`.

`-f` keeps the listed keys of an item, of each item in a list, and of each entry in the `items` of a folder or a search.

## Errors and exit codes

Errors are JSON on standard error.

```json
{
  "error": {
    "status_code": 404,
    "type": "NotFound",
    "message": "Resource not found: https://example.org/++api++/missing",
    "method": "GET",
    "url": "https://example.org/++api++/missing"
  }
}
```

| Code | Meaning |
|---|---|
| 0 | Success. |
| 1 | Unexpected error, or a refused confirmation. |
| 2 | Invalid usage, invalid JSON, or a destructive command without `--yes` and without a terminal. |
| 3 | Configuration: unknown profile, missing secret, or no site configured. |
| 4 | Not authenticated, not allowed, or the item is locked. `info` and `profile test` exit with 4 when the site rejected the profile's credentials. |
| 5 | Not found. |
| 6 | Invalid request or conflict. |
| 7 | Refused by `--read-only` or a read-only profile. |
| 8 | The site could not be reached. |
| 9 | Server error. |

## Confirmation

`delete`, `users delete`, and `groups delete` ask for confirmation.
Without a terminal they require `--yes`.
With `--dry-run` they need neither.

## Related

- {ref}`reference-configuration` describes profiles and environment variables.
- {ref}`howto-agents` uses the command line from a coding agent.
