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

<!-- source: src/plone_client/cli/content.py, src/plone_client/cli/site.py, src/plone_client/cli/profile.py -->

`plone-client --help` lists the commands in the groups below, and each command group splits its subcommands into **Browse** (read only) and **Write** panels.

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
| `download <ref>` | Download the file or image of an item. |

### Site users, settings, and types

| Command | Does |
|---|---|
| `types [type]` | List content types, or show the JSON schema of one. |
| `vocabulary [name]` | List vocabularies, or the terms of one. |
| `users list`, `get` / `create`, `update`, `delete` | Browse and manage users. |
| `groups list`, `get` / `create`, `delete` / `add-member`, `remove-member` | Browse and manage groups and their members. |
| `registry list`, `get` / `set` | Browse and change registry records. |
| `aliases list` / `add`, `remove` | Browse and manage URL aliases. |

### Advanced

| Command | Does |
|---|---|
| `request <method> <ref>` | Send any request, for services without a command. |

### Connection, profiles, and agents

| Command | Does |
|---|---|
| `info` | Show the profile, site, and user the command line connects with, and the Plone version. |
| `profile list`, `show` / `add`, `use`, `defaults`, `remove` / `set-secret`, `test` | Manage connection profiles; `add` and `defaults` take `--timeout`, `--verify` (`true`, `false`, or a CA bundle path), `--retries`, and `--backoff`. |
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
| 4 | Not authenticated, not allowed, or the item is locked. |
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
