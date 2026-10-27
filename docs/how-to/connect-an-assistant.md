---
myst:
  html_meta:
    "description": "Connect a chat assistant or an agent to a Plone site through the plone-client MCP server."
    "property=og:description": "Connect a chat assistant or an agent to a Plone site through the plone-client MCP server."
    "property=og:title": "Connect an assistant through the MCP server"
---

(howto-assistant)=

# Connect an assistant through the MCP server

This guide shows you how to give an MCP client, such as Claude Desktop or Claude Code, access to a Plone site through the plone-client MCP server.

## Install the server

Install plone-client as a tool with the `mcp` extra.
Add the `markdown` extra too, on Python 3.12 or later, so the assistant can write pages in Markdown.

::::{tab-set}
:sync-group: installer

:::{tab-item} uv
:sync: uv

```shell
uv tool install "plone-client[mcp,markdown]"
```
:::

:::{tab-item} pipx
:sync: pip

```shell
pipx install "plone-client[mcp,markdown]"
```
:::
::::

## Add a profile for the site

The server connects with a profile, so the password stays in the keyring and never reaches the assistant.

```shell
plone-client profile add blog --url https://example.org --username editor
plone-client profile test blog
```

To keep the assistant from changing anything, make the profile read-only.

```shell
plone-client profile add blog-ro --url https://example.org --username editor --read-only
```

If the profile's URL is the backend rather than the Volto frontend, add the URL of the frontend, so the assistant can learn the site's blocks.

```shell
plone-client profile add local --url http://localhost:8080/Plone --username admin --frontend-url http://localhost:3000
```

Refer to {ref}`howto-profiles` for the other ways to keep a secret.

## Register the server with your assistant

::::{tab-set}

:::{tab-item} Claude Code

Add the server to the current project.

```shell
claude mcp add plone-blog -- plone-client mcp --profile blog
```

Pass `--scope user` to make it available in every project, or `--scope project` to share it with the project's other contributors in `.mcp.json`.
:::

:::{tab-item} Claude Desktop

Add the server to `claude_desktop_config.json`, in {menuselection}`Settings --> Developer --> Edit Config`, then restart Claude Desktop.

```json
{
  "mcpServers": {
    "plone-blog": {
      "command": "plone-client",
      "args": ["mcp", "--profile", "blog"]
    }
  }
}
```

If Claude Desktop cannot find `plone-client`, write its full path in `command`, which `which plone-client` prints.
:::

:::{tab-item} Other clients

Configure a server that runs this command over standard input and output.

```shell
plone-client mcp --profile blog
```
:::
::::

## Serve several sites from one server

If you work with several sites, register one server for all of them rather than one server per site.
Add a profile for each site first, with a description that says what the site is, because the assistant reads it to pick the site.

```shell
plone-client profile add docs --url https://docs.example.org --username editor --description "Documentation, production"
```

Name the profiles with `--site`, or serve every profile with `--all`.

```shell
claude mcp add --scope user plone -- plone-client mcp --site blog --site docs
```

To serve the same set of sites from several places, save them as a group, and serve the group.

```shell
plone-client profile group-set customer blog docs
claude mcp add --scope user plone -- plone-client mcp --group customer
```

A site added to the group later is served the next time the assistant starts the server.
Each tool then takes a `site` argument, and the `list_sites` tool describes the sites.
A read-only profile stays read-only: the server refuses to change that site, and still changes the others.

## Preview changes first

To see what the assistant would change without changing anything, start the server in a dry run.

```shell
claude mcp add plone-blog-preview -- plone-client mcp --profile blog --dry-run
```

Each tool that changes the site then returns the requests it would send.

## Check the connection

Ask the assistant to call the `site_info` tool.
It reports the site, the user the server is logged in as, and whether it is read-only or in a dry run.

## Related

- {ref}`reference-assistant-server` lists the tools and their arguments.
- {ref}`explanation-interfaces` compares the MCP server with the command line and the agent skill.
- {ref}`howto-agents` sets up a coding agent with the command line instead.
