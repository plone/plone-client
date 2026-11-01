---
myst:
  html_meta:
    "description": "Connect Claude Desktop to a Plone site, step by step: install plone-client, add a profile, edit the configuration file, restart, and check the connection."
    "property=og:description": "Connect Claude Desktop to a Plone site, step by step: install plone-client, add a profile, edit the configuration file, restart, and check the connection."
    "property=og:title": "Connect Claude Desktop to a Plone site"
---

(howto-claude-desktop)=

# Connect Claude Desktop to a Plone site

This guide shows you how to let Claude Desktop read and change a Plone site.
You install plone-client in a terminal, tell Claude Desktop where to find it, and restart the application.

Claude Desktop starts the plone-client {term}`MCP` server by itself, each time it opens, so you never start the server by hand.

You need the following.

- [Claude Desktop](https://claude.ai/download).
- [uv](https://docs.astral.sh/uv/getting-started/installation/), which installs plone-client.
- The address of a Plone site, with a username and a password.
  To try this on a local site, follow {ref}`howto-run-a-site` first.

## Install plone-client

In a terminal, install plone-client with the MCP server and Markdown support.

```shell
uv tool install --python 3.13 "plone-client[mcp,markdown]"
```

Check that it works.

```shell
plone-client --version
```

If the terminal answers that it cannot find `plone-client`, run `uv tool update-shell`, then open a new terminal.

## Add your site as a profile

A {term}`profile` stores the site's address and your username.
The password goes into your {term}`keyring`, so Claude never sees it.

```shell
plone-client profile add blog --url https://example.org --username editor
```

Replace `blog`, the address, and `editor` with your own.
When asked, type the password.

To let Claude read the site but not change it, add `--read-only` to that command.
This is the safest way to start on a real site; {ref}`howto-protect` explains your other options.

Check that the profile can log in.

```shell
plone-client profile test blog
```

## Find the full path of plone-client

Claude Desktop does not start from your terminal, so it may not find a program by its name alone.
Give it the full path.

::::{tab-set}
:sync-group: os

:::{tab-item} macOS and Linux
:sync: mac-linux

```shell
which plone-client
```
:::

:::{tab-item} Windows
:sync: windows

```shell
where plone-client
```
:::
::::

Copy the line that this prints.
You need it in the next step.

## Add the server to the configuration file

Open the configuration file.

1. Open the Settings window from the Claude menu in your system's menu bar, not from inside the conversation window.
2. Select {guilabel}`Developer` in the sidebar.
3. Select {guilabel}`Edit Config`.

Claude Desktop creates the file if it does not exist, and shows it to you.
Open it in a text editor.
If you cannot find the button, open the file directly.

| System | File |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |
| Linux | `~/.config/Claude/claude_desktop_config.json` |

Add the server.
In `command`, write the full path that you copied.
In `args`, write the name of your profile in place of `blog`.

::::{tab-set}
:sync-group: os

:::{tab-item} macOS and Linux
:sync: mac-linux

```json
{
  "mcpServers": {
    "plone-blog": {
      "command": "/Users/you/.local/bin/plone-client",
      "args": ["mcp", "--profile", "blog"]
    }
  }
}
```
:::

:::{tab-item} Windows
:sync: windows

Write each backslash in the path twice.

```json
{
  "mcpServers": {
    "plone-blog": {
      "command": "C:\\Users\\you\\.local\\bin\\plone-client.exe",
      "args": ["mcp", "--profile", "blog"]
    }
  }
}
```
:::
::::

If the file is empty, paste this as its whole content.
If it already has content, keep that content.
Add `mcpServers` next to the other top-level keys, with a comma between them.
If `mcpServers` is already there, add `plone-blog` inside it, next to the other servers.

Save the file.

## Restart Claude Desktop

Quit Claude Desktop completely, then open it again.
Closing the window is not enough, because the application keeps running and does not read the file again.

- On macOS, select {menuselection}`Claude --> Quit Claude`.
- On Windows, right-click the Claude icon in the notification area, and quit from there.

## Check the connection

1. Select the {guilabel}`+` button below the chat box.
2. Select {guilabel}`Connectors`.
3. Look for `plone-blog` in the list.

Then ask Claude for this.

```text
Use the site_info tool of plone-blog, and tell me which site and user you see.
```

Claude asks for your approval before it uses a {term}`tool`.
It answers with the address of your site, your username, and whether the site is read-only.

Your site is connected.
Before you give Claude real work, read {ref}`howto-protect`.

## If the server does not appear

Run the same command that Claude Desktop runs, with your full path, in a terminal.

```shell
/Users/you/.local/bin/plone-client mcp --profile blog
```

If it is working, it prints nothing and waits; press {kbd}`Control+C` to stop it.
If it prints an error, the error says what is wrong.

If that works, read the logs of Claude Desktop.
The file `mcp.log` reports connections, and `mcp-server-plone-blog.log` holds what the server printed.

| System | Folder |
|---|---|
| macOS | `~/Library/Logs/Claude` |
| Windows | `%APPDATA%\Claude\logs` |
| Linux | `~/.config/Claude/logs` |

| What you see | What to do |
|---|---|
| `plone-blog` is not listed, and nothing in the logs mentions it | The file has a JSON error, such as a missing comma, or Claude Desktop did not restart. Check the commas and quit the application again. |
| `ENOENT` or `spawn` in `mcp.log` | `command` is not the full path. Run `which plone-client` again and copy its answer. |
| `Unknown tool: create_page`, or the tool is missing | Reinstall with the `markdown` extra, as this guide shows. |
| The tools that change the site are missing | The profile is {term}`read-only`, or the server runs with `--tool`. |
| An error about a missing secret or the keyring | See {ref}`howto-profiles` for other ways to keep the password. |

After you edit the configuration file, restart Claude Desktop again.
{ref}`howto-troubleshoot` covers the errors that come from the site.

## Related

- {ref}`howto-assistant` connects other clients, and serves several sites from one server.
- {ref}`howto-protect` decides what an assistant can see and do.
- {ref}`reference-assistant-server` lists the tools.
