---
myst:
  html_meta:
    "description": "Decide what an assistant can see and do on a Plone site through plone-client: what the model reads, read-only and dry run modes, short tool lists, HTTP, and the limits of each."
    "property=og:description": "Decide what an assistant can see and do on a Plone site through plone-client: what the model reads, read-only and dry run modes, short tool lists, HTTP, and the limits of each."
    "property=og:title": "Protect a site from an agent"
---

(howto-protect)=

# Protect a site from an agent

This guide shows you how to decide what an {term}`assistant` or a {term}`coding agent` can see and do on a Plone site, and how to limit it.
Start from the top: each layer below narrows the one before.

## Give it a user with few permissions

Everything an agent does goes through the Plone user of its {term}`profile`, so Plone's own permissions bound everything else on this page.
A user who can only edit `/news` cannot change anything else, whatever the agent tries.
Use a dedicated user with the `Editor` role on the folders it needs, not `admin`.
{ref}`howto-users-sharing` creates one.

(howto-protect-enforcement)=

## Know who enforces what

Some layers below stop a request, and some only describe what should happen.
Rely on the first kind; treat the second as guidance.

| Layer | Enforced by | When | Source |
|---|---|---|---|
| Plone permissions | Plone | On every request, on the site | The site; plone-client sends every request as the profile's user |
| {term}`Read-only` profile or client | plone-client, in the client | Before the request is sent | `src/plone_client/client.py` `PloneClient.request` |
| `transitions` of a profile or client | plone-client, in the client | Before the request is sent | `src/plone_client/client.py` `PloneClient._check_transition` |
| `--tool` allowlist | The MCP server | When the server starts; a tool left out does not exist for the model | `src/plone_client/mcp_server.py` `build_server` |
| {term}`Dry run` | Nothing: it is a preview mode | Changes are logged instead of sent, and reported as planned | `src/plone_client/client.py` `PloneClient.request` |
| The {term}`skill`'s rules | Nothing: they are guidance the agent may follow | Whenever the agent reads them | `src/plone_client/skill/SKILL.md` |
| The agent application's permissions and confirmations | The agent application, outside plone-client | Before the agent runs a command or a tool | Your agent's settings |
| Your approval of a plan | You, only if your setup makes it a gate | When you restart a server without `--dry-run`, or your code sends the change | {ref}`tutorial-editorial-assistant`, {ref}`howto-custom-agent` |

## Know what the model sees

<!-- source: src/plone_client/mcp_server.py _instructions, Site.summary, site_info, _per_site -->

| The model sees | The model never sees |
|---|---|
| The name, URL, description, and mode of each site the server serves. | Passwords and tokens: they stay in the {term}`keyring` or the environment of the server. |
| The Plone user name and the Plone version, through `site_info`. | {term}`Profiles <profile>` that the server does not serve. |
| Everything that user can read through the {term}`tools <tool>` on offer. | Tools left out with `--tool`. |
| The {term}`instructions` and the description of each tool. | |

Treat what the model reads from a site as untrusted input.
A page written by a visitor or another editor reaches the model the same way your prompt does, and it can ask for things that you did not.
The layers below limit what such a request can do.

With the command line, the same holds for the {term}`skill`, with one difference: an agent in a terminal can run any command you allow, so `plone-client` is not its only way out.
Limit the agent with its own permission settings as well.

## Make production read-only

<!-- source: src/plone_client/mcp_server.py Sites.from_profiles, build_server, _instructions; src/plone_client/client.py request -->

A {term}`read-only` profile refuses every change in the client, before the change leaves your computer.
A tool can still read from the site first, such as the schema of a type.
Make every site other than a local one read-only, and keep a separate profile for the work that needs to write.

<!-- check: start -->

<!-- check: stdin admin -->
```shell
plone-client profile add production --url http://localhost:8080/Plone --username admin --read-only --use
```

<!-- check: exit 7 -->
```shell
plone-client delete /news --yes
```

```json
{
  "error": {
    "type": "PloneReadOnlyError",
    "message": "DELETE /news refused: the client is read-only"
  }
}
```

An MCP server of only read-only sites offers only the tools that read, and refuses to start with a tool that writes.

<!-- check: exit 3 -->
```shell
plone-client mcp --tool search --tool delete_content
```

```json
{
  "error": {
    "type": "PloneConfigurationError",
    "message": "This server does not offer delete_content (it offers: block_types, call_service, content_types, get_content, get_navigation, get_translations, get_vocabulary, get_workflow, get_working_copy, list_blocks, list_children, search, site_info)"
  }
}
```

With several sites and at least one that accepts changes, the server offers the tools that write and refuses them on the read-only site, also before sending anything.

```{important}
`call_service` is offered in every mode, because it can read any service.
It follows the same rules: on a read-only site, it refuses a request that would change something.
```

## Let it submit, not publish

<!-- source: src/plone_client/client.py PloneClient._check_transition; src/plone_client/profiles.py Profile.transitions -->

A profile with `transitions` runs only the workflow {term}`transitions <transition>` it lists, and refuses the others before they leave your computer.
Give the assistant a profile that can submit an item for review, and keep publishing for a person.

<!-- check: stdin admin -->
```shell
plone-client profile add review --url http://localhost:8080/Plone --username admin --transition submit
```

<!-- check: exit 7 -->
```shell
plone-client -p review workflow /news/release-party publish
```

```json
{
  "error": {
    "type": "PloneTransitionError",
    "message": "POST /news/release-party/@workflow/publish refused: the client allows only these transitions: submit"
  }
}
```

```shell
plone-client -p review workflow /news/release-party submit -f review_state
```

```json
{
  "review_state": "pending"
}
```

Repeat `--transition` to allow more, such as `retract`.
The same list works in Python, as `PloneClient(..., transitions=["submit"])`, and in `PLONE_CLIENT_TRANSITIONS`.
The MCP server shows it to the model in `list_sites`, and refuses the other transitions, also through `call_service`.

```{versionadded} 1.0.0a5
The `transitions` setting.
```

## Preview with a dry run

A {term}`dry run` is not a safety boundary, it is a way to look before you approve.
Compare the two.

| | {term}`Read-only` | {term}`Dry run` |
|---|---|---|
| Set with | `--read-only`, or `read_only = true` in a profile | `-n`, `--dry-run` |
| Applies to | One site or one profile | The whole command or server |
| A change | Fails with an error, exit code 7 | Succeeds, sends nothing, and reports what it would send |
| An agent notices | Yes, and the skill tells it to stop | Only from `dry_run` in the answer |
| Use it for | Sites the agent must not change | Reviewing a plan before you allow it |

{ref}`howto-preview-changes` has the details.

## Offer fewer tools

<!-- source: src/plone_client/mcp_server.py build_server (wanted); src/plone_client/cli/mcp.py -->

`--tool` is an allowlist: the server offers only the tools you name, and with them, only the {term}`resources <resource>` of the same data.
A shorter list also costs less context, because the model reads the description of every tool in every conversation.
Start from one of these sets.
{ref}`reference-assistant-server-tools` lists all the tools.

Reader
: Answers questions, and changes nothing.

  ```shell
  plone-client -p production mcp --tool site_info --tool search --tool get_content --tool list_children --tool list_blocks --tool get_navigation --tool content_types --tool block_types --tool get_workflow --tool get_vocabulary
  ```

Editor
: Writes and edits pages, and leaves publishing and deleting to you.

  <!-- check: stdin admin -->
  ```shell
  plone-client profile add staging --url http://localhost:8080/Plone --username admin --frontend-url http://localhost:3000
  ```

  ```shell
  plone-client -p staging mcp --tool site_info --tool search --tool get_content --tool list_children --tool list_blocks --tool content_types --tool block_types --tool create_page --tool add_blocks --tool update_block --tool update_content
  ```

Migrator
: Creates and moves content in bulk, and cannot delete it.

  ```shell
  plone-client -p staging mcp --tool site_info --tool search --tool get_content --tool list_children --tool content_types --tool create_content --tool create_content_with_files --tool upload_tree --tool copy_content --tool move_content --tool run_transition
  ```

<!-- check: stop -->

None of these sets has `call_service`, which reaches every service the user can use, or `delete_content`.
Add them only for a task that needs them.

```{warning}
`create_content_with_files`, `create_page`, and `upload_tree` read local files, from paths the model chooses.
Any file that the account running the server can read can end up on the site.
Run the server under an account with little to read, or leave those tools out.
```

## Keep confirmation for the command line

<!-- source: src/plone_client/skill/SKILL.md; src/plone_client/mcp_server.py delete_content -->

The command line asks for {term}`confirmation` before `delete`, `users delete`, and `groups delete`, and refuses them without a terminal unless given `--yes`.
The skill tells an agent never to pass `--yes` unless you confirmed the exact items.
That is guidance the agent follows, not a barrier: an agent that ignores the skill can pass `--yes`.

The MCP server has no such step.
`delete_content` deletes what the model names, and its annotations mark it as destructive so that a client can ask you first.
Whether it asks depends on the client.
Keep the tool out of the list unless you need it.

## Remember that blocks take no lock

<!-- source: src/plone_client/mcp_server.py _block_tools, Site.lock -->

`add_blocks`, `update_block`, `remove_blocks`, and `set_blocks` read an item, change its blocks, and save them.
The server runs one tool at a time per site, so two calls to one server do not collide.
An editor working in Volto at the same moment is another matter: what they save between the read and the write can be lost.
Let an agent work on staging, or on items nobody is editing.

## Serve over HTTP with care

<!-- source: src/plone_client/mcp_server.py BearerToken, HTTPSettings, http_app; src/plone_client/credentials.py -->

The server over HTTP needs a token of at least 32 characters on every request, and it never starts without one.
Clients of the server never get the credentials of the site, and they cannot point it at another site.

Before you deploy it, go through the checklist in {ref}`reference-assistant-server-http`.

## Related

- {ref}`explanation-interfaces` compares the MCP server, the command line, and the skill.
- {ref}`howto-agents` sets up a coding agent.
- {ref}`howto-assistant` connects an assistant.
