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
{ref}`reference-cli-options` lists the arguments and options of every command, and `plone-client <command> --help` prints the same.

The examples on this page run against the {term}`Compose site`, with the sample content of {ref}`howto-run-a-site`.

<!-- check: start -->

```shell
export PLONE_CLIENT_URL=http://localhost:8080/Plone
export PLONE_CLIENT_USERNAME=admin
export PLONE_CLIENT_PASSWORD=admin
```

(reference-cli-global-options)=

## Global options

<!-- source: docs/_generate/cli_options.py, from src/plone_client/cli/app.py -->

```{include} ../_generated/cli-global-options.md
```

`-p`, `--config`, `-n`, `-f`, `-c`, and `-v` work anywhere on the line.
`--url`, `-u`, `--read-only`, and `--version` must come before the command, because `profile add` has options with the same names.

## Commands

`plone-client --help` lists the commands in the groups below, and each command group splits its subcommands into **Browse** (read only) and **Write** panels.
In a terminal, the help draws each group as a box.
When the output goes to a pipe or a file, as it does for scripts and coding agents, the help is plain text with the same groups as titled sections.
To get plain help in a terminal too, set `TYPER_USE_RICH=0`.

`<ref>` accepts a path, a URL inside the site, `uid:<UID>`, or a `resolveuid` link.

### Read content

| Command | Does |
|---|---|
| {ref}`get <cli-get>` | Print an item. |
| {ref}`ls <cli-ls>` | List the items inside a folder, in order. |
| {ref}`search <cli-search>` | Search the catalog, inside a folder or the whole site. |
| {ref}`resolve <cli-resolve>` | Print the path, URL, and {term}`UID` of an item. |
| {ref}`blocks <cli-blocks>` | Summarize the {term}`blocks <block>` of an item, nested ones included. |
| {ref}`history <cli-history>` | List the versions and {term}`workflow` history of an item. |
| {ref}`sharing <cli-sharing>` | Show the local roles of an item. |

### Change content

| Command | Does |
|---|---|
| {ref}`create <cli-create>` | Create an item inside a folder. |
| {ref}`create-page <cli-create-page>` | Create a page from Markdown or HTML, converted to blocks; see {ref}`reference-configuration-blocks`. Needs the `markdown` extra. |
| {ref}`create-with-files <cli-create-with-files>` | Create an item, upload files and images inside it, and set its {term}`lead image`. |
| {ref}`update <cli-update>` | Change fields of an item. |
| {ref}`workflow <cli-workflow>` | Show the workflow state and {term}`transitions <transition>` of an item, or run a transition. |
| {ref}`copy <cli-copy>` | Copy items into a folder. |
| {ref}`move <cli-move>` | Move items into a folder. |
| {ref}`order <cli-order>` | Move an item within its folder. |
| {ref}`delete <cli-delete>` | Delete items. |

### Files

| Command | Does |
|---|---|
| {ref}`upload <cli-upload>` | Upload files as `File` or `Image` items. |
| {ref}`upload-tree <cli-upload-tree>` | Upload the contents of a local folder as pages, files, and images, keeping its structure. |
| {ref}`download <cli-download>` | Download the file or image of an item. |

### Site users, settings, and types

| Command | Does |
|---|---|
| {ref}`types <cli-types>` | List {term}`content types <content type>`, or show the JSON schema of one. |
| {ref}`block-types <cli-block-types>` | List the blocks of the site, or show the docs, schema, and variations of one. |
| {ref}`vocabulary <cli-vocabulary>` | List vocabularies, or the terms of one. |
| {ref}`users <cli-users>` | `list`, `get` / `create`, `update`, `delete`: browse and manage users. |
| {ref}`groups <cli-groups>` | `list`, `get` / `create`, `delete` / `add-member`, `remove-member`: browse and manage groups and their members. |
| {ref}`registry <cli-registry>` | `list`, `get` / `set`: browse and change registry records. |
| {ref}`aliases <cli-aliases>` | `list` / `add`, `remove`: browse and manage URL aliases. |

### Advanced

| Command | Does |
|---|---|
| {ref}`request <cli-request>` | Send any request, for services without a command. |
| {ref}`mcp <cli-mcp>` | Serve sites as an {term}`MCP` server over standard input and output, or over HTTP; see {ref}`reference-assistant-server`. Needs the `mcp` extra. |
| {ref}`mcp-token <cli-mcp-token>` | `generate`, `set`, `delete`: manage the token clients send to `mcp --http`, kept in the {term}`keyring`; see {ref}`reference-assistant-server-http`. |

`create-page`, `create-with-files`, and `upload-tree` run the {term}`operations <operation>` of {mod}`plone_client.operations` and print their result: `created`, `changed`, and every request in `requests`.
When one of them stops part way, the error on standard error also has a `result` with what was already done, and the exit code is that of the request that failed.

### Connection, profiles, and agents

| Command | Does |
|---|---|
| {ref}`info <cli-info>` | Show the {term}`profile`, site, and user the command line connects with, and the Plone version. If the site rejected the profile's credentials, the output has `credentials_rejected: true` and a `message` that names the fix, and the exit code is 4. |
| {ref}`profile <cli-profile>` | `list`, `show` / `add`, `use`, `defaults`, `remove` / `set-secret`, `test`: manage connection profiles. |
| {ref}`profile groups <cli-profile-groups>` | `groups` / `group-set`, `group-remove`: list, create or replace, and remove groups of profiles; see {ref}`reference-configuration-groups`. |
| {ref}`skill <cli-skill>` | `show` / `install`: print the agent {term}`skill`, or install it. |

In the group rows, `/` separates the panels of the group's help: Browse, then Write, then Membership or Connection.

## Field values

`create` and `update` merge field values from these options, each one winning over the previous.

| Order | Option | Value |
|---|---|---|
| 1 | `-d`, `--data` | A JSON object, `@file.json` to read a file, or `-` to read standard input. |
| 2 | `-s`, `--set`, repeatable | `key=text` sets a string; `key:=json` sets any JSON value. |
| 3 | `--title`, `--description` | The title and the description. |

`create` adds a title block and a description block to an item created without `blocks`, unless given `--no-blocks`.

(reference-cli-output)=

## Output

Results are JSON on standard output, indented unless `-c` is given.

`ls` prints a list of items, each with its `@id`, its `@type`, and the columns of the catalog.

```shell
plone-client ls /about
```

```json
[
  {
    "@id": "http://localhost:8080/Plone/about/team",
    "@type": "Document",
    "description": "The people behind the site.",
    "effective": "1969-12-31T00:00:00+00:00",
    "end": null,
    "getObjSize": "0 KB",
    "getRemoteUrl": null,
    "head_title": null,
    "image_field": "",
    "image_scales": null,
    "mime_type": "text/plain",
    "nav_title": null,
    "review_state": "private",
    "start": null,
    "title": "Team",
    "type_title": "Page"
  }
]
```

`search` prints the same list.
`--count` prints only the total.

```shell
plone-client search -t Image -f @id,title,image_field
```

```json
[
  {
    "@id": "http://localhost:8080/Plone/media/logo.png",
    "title": "Logo",
    "image_field": "image"
  }
]
```

```shell
plone-client search -t Image --count
```

```json
{
  "items_total": 1
}
```

Commands that create or change an item print `@id`, `@type`, `UID`, `id`, `title`, and `review_state`.

```shell
plone-client update /about/team --description "The people behind the site"
```

```json
{
  "@id": "http://localhost:8080/Plone/about/team",
  "@type": "Document",
  "UID": "d5ad47d7684449d4b73788eaa13d8b76",
  "id": "team",
  "title": "Team",
  "review_state": "private"
}
```

`-f` keeps the keys you name, and `-c` puts the result on one line.

```shell
plone-client update /about/team --description "The people behind the site" -f id,review_state -c
```

```json
{"id": "team", "review_state": "private"}
```

`--full` prints the whole item, which has every field of its {term}`content type`.

```shell
plone-client update /about/team --description "The people behind the site" --full -c | jq 'length'
```

```text
39
```

`-f` keeps the listed keys of an item, of each item in a list, and of each entry in the `items` of a folder or a search.
On an answer with `items`, as `request` returns, it applies to the answer itself as soon as one of the keys is at its top level.
A key that is not there is left out without an error, and an entry with none of the keys prints as `{}`.

```shell
plone-client ls /about -f id -c
```

```json
[{}]
```

`ls` and `search` results have no `id` key: use `@id`.

## Errors and exit codes

Errors are JSON on standard error.

<!-- check: exit 5 -->
```shell
plone-client get /missing
```

```json
{
  "error": {
    "status_code": 404,
    "type": "NotFound",
    "message": "Resource not found: http://localhost:8080/Plone/++api++/missing",
    "method": "GET",
    "url": "http://localhost:8080/Plone/++api++/missing"
  }
}
```

<!-- check: stop -->

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

(reference-cli-confirmation)=

## Confirmation

`delete`, `users delete`, and `groups delete` ask for confirmation.
Without a terminal they require `--yes`.
With `--dry-run` they need neither.

(reference-cli-options)=

## Options of each command

<!-- source: docs/_generate/cli_options.py, from the Typer application in src/plone_client/cli/ -->

```{include} ../_generated/cli-commands.md
```

## Related

- {ref}`reference-configuration` describes profiles and environment variables.
- {ref}`reference-cheat-sheet` lists the commands by task.
- {ref}`howto-everyday` has recipes.
- {ref}`howto-agents` uses the command line from a coding agent.
