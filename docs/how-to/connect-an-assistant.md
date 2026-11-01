---
myst:
  html_meta:
    "description": "Connect a chat assistant or an agent to a Plone site through the plone-client MCP server: Claude Code, Claude Desktop, Cursor, VS Code, Codex, Gemini CLI, or your own client."
    "property=og:description": "Connect a chat assistant or an agent to a Plone site through the plone-client MCP server: Claude Code, Claude Desktop, Cursor, VS Code, Codex, Gemini CLI, or your own client."
    "property=og:title": "Connect an assistant through the MCP server"
---

(howto-assistant)=

# Connect an assistant through the MCP server

This guide shows you how to give an {term}`assistant`, or any other client of the {term}`MCP`, access to a Plone site through the plone-client MCP server.

An MCP client needs one of two things.

- For a server on your computer, a command to start, which speaks over standard input and output: `plone-client mcp --profile blog`.
- For a server somewhere else, a URL and a token.

The rest of this guide sets those up, and shows where each client keeps them.

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

To skip the installation, a client can start the server with `uvx`.
Use `uvx` as the command, and `--from`, `plone-client[mcp]`, `plone-client`, `mcp`, `--profile`, and `blog` as its arguments.
The first start takes longer, and the profile still has to exist, so you need the `cli` extra once to create it.

## Add a profile for the site

The server connects with a {term}`profile`, so the password stays in the {term}`keyring` and never reaches the assistant.

```shell
plone-client profile add blog --url https://example.org --username editor
plone-client profile test blog
```

To keep the assistant from changing anything, make the profile {term}`read-only`.

```shell
plone-client profile add blog-ro --url https://example.org --username editor --read-only
```

If the profile's URL is the backend rather than the {term}`Volto` frontend, add the URL of the frontend, so the assistant can learn the site's blocks.

```shell
plone-client profile add local --url http://localhost:8080/Plone --username admin --frontend-url http://localhost:3000
```

Refer to {ref}`howto-profiles` for the other ways to keep a secret.

(howto-assistant-register)=

## Register the server with your client

The JSON entry below is the same for most clients; only the file and, in places, the key differ.

::::{tab-set}
:sync-group: agent

:::{tab-item} Claude Code
:sync: claude-code

Add the server to the current project.

```shell
claude mcp add plone-blog -- plone-client mcp --profile blog
```

Pass `--scope user` to make it available in every project, or `--scope project` to share it with the project's other contributors in `.mcp.json`.
:::

:::{tab-item} Claude Desktop
:sync: claude-desktop

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

:::{tab-item} Cursor
:sync: cursor

Add the server to `.cursor/mcp.json` in the project, or to `~/.cursor/mcp.json` for every project.

```json
{
  "mcpServers": {
    "plone-blog": {
      "type": "stdio",
      "command": "plone-client",
      "args": ["mcp", "--profile", "blog"]
    }
  }
}
```
:::

:::{tab-item} VS Code
:sync: copilot

Add the server to `.vscode/mcp.json` in the project.
The top-level key is `servers`, not `mcpServers`.

```json
{
  "servers": {
    "plone-blog": {
      "type": "stdio",
      "command": "plone-client",
      "args": ["mcp", "--profile", "blog"]
    }
  }
}
```
:::

:::{tab-item} Codex
:sync: codex

Add the server with the command.

```shell
codex mcp add plone-blog -- plone-client mcp --profile blog
```

Or write it to `~/.codex/config.toml`, or to `.codex/config.toml` in a trusted project.

```toml
[mcp_servers.plone-blog]
command = "plone-client"
args = ["mcp", "--profile", "blog"]
```
:::

:::{tab-item} Gemini CLI
:sync: google

Add the server to `.gemini/settings.json` in the project, or to `~/.gemini/settings.json` for every project.

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
:::

:::{tab-item} Other clients
:sync: other

Most clients read this shape, under some name, from an `mcp.json` file.

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

If yours takes something else, it needs the same two things: the command `plone-client`, and the arguments `mcp`, `--profile`, and `blog`.
:::
::::

Your own Python program is a client too.
{ref}`howto-assistant-python` shows how it connects.

(howto-assistant-check)=

## Check the connection

Ask the assistant to call the `site_info` {term}`tool`.
It reports the site, the user the server is logged in as, and whether it is read-only or in a {term}`dry run`.

## Serve several sites from one server

If you work with several sites, register one server for all of them rather than one server per site.
Add a profile for each site first, with a description that says what the site is, because the assistant reads it to pick the site.

```shell
plone-client profile add docs --url https://docs.example.org --username editor --description "Documentation, production"
```

Name the profiles with `--site`, or serve every profile with `--all`.
In the arguments of the entry you registered, write them instead of `--profile`.

```shell
plone-client mcp --site blog --site docs
```

To serve the same set of sites from several places, save them as a {term}`group`, and serve the group.

```shell
plone-client profile group-set customer blog docs
plone-client mcp --group customer
```

A site added to the group later is served the next time the assistant starts the server.
Each tool then takes a `site` argument, and the `list_sites` tool describes the sites.
A read-only profile stays read-only: the server refuses to change that site, and still changes the others.
{ref}`tutorial-editorial-assistant` builds this setup, step by step.

## Preview changes first

To see what the assistant would change without changing anything, add `--dry-run` to the arguments of the server.

```shell
plone-client mcp --profile blog --dry-run
```

Each tool that changes the site then returns the requests it would send.

## Serve over HTTP

Some assistants connect to a URL instead of starting a command, and a server can then run on another machine.
The examples below use a local site; {ref}`howto-run-a-site` starts one.

<!-- check: start -->

<!-- check: stdin admin -->
```shell
plone-client profile add local --url http://localhost:8080/Plone --username admin --frontend-url http://localhost:3000
```

Make a token first; the server refuses every request without it.
The token is stored in the keyring and printed once, as `token`.
To read it, this example uses [jq](https://jqlang.org/).

```shell
export TOKEN=$(plone-client mcp-token generate | jq -r .token)
```

Generating a token replaces the one stored before, so run it again only to change the token, then restart the server.

Start the server with `--http`.
It listens on `http://127.0.0.1:8000/mcp` unless given `--host` and `--port`.
It normally stays in the foreground of its own terminal; here it runs in the background, so that the next commands can use it.

```shell
plone-client mcp --profile local --http > server.log 2>&1 &
export SERVER=$!
sleep 3
cat server.log
```

```text
plone-client: serving MCP at http://127.0.0.1:8000/mcp
```

Without the token, the server answers `401`.

```shell
curl --silent --output /dev/null --write-out '%{http_code}\n' --request POST http://127.0.0.1:8000/mcp
```

```text
401
```

With it, the server takes part in the protocol: this is the first message of every client.

```shell
curl --silent --request POST http://127.0.0.1:8000/mcp --header "Authorization: Bearer $TOKEN" --header "Content-Type: application/json" --header "Accept: application/json, text/event-stream" --data '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "curl", "version": "1"}}}' | sed -n 's/^data: //p' | jq -c '.result | {protocolVersion, serverInfo: .serverInfo.name}'
```

```text
{"protocolVersion":"2025-06-18","serverInfo":"plone-client"}
```

Then register the URL with your client, sending the token in the `Authorization` header.
Keep the token out of files that you commit: each client below has its own way.

::::{tab-set}
:sync-group: agent

:::{tab-item} Claude Code
:sync: claude-code

<!-- check: skip -->
```shell
claude mcp add --transport http plone-blog http://127.0.0.1:8000/mcp --header "Authorization: Bearer $TOKEN"
```
:::

:::{tab-item} Cursor
:sync: cursor

Cursor reads the token from an environment variable.

<!-- check: skip -->
```json
{
  "mcpServers": {
    "plone-blog": {
      "url": "http://127.0.0.1:8000/mcp",
      "headers": {
        "Authorization": "Bearer ${env:PLONE_MCP_TOKEN}"
      }
    }
  }
}
```
:::

:::{tab-item} VS Code
:sync: copilot

VS Code asks for the token once, and stores it.

<!-- check: skip -->
```json
{
  "inputs": [
    {
      "type": "promptString",
      "id": "plone-token",
      "description": "Token of the Plone MCP server",
      "password": true
    }
  ],
  "servers": {
    "plone-blog": {
      "type": "http",
      "url": "http://127.0.0.1:8000/mcp",
      "headers": {
        "Authorization": "Bearer ${input:plone-token}"
      }
    }
  }
}
```
:::

:::{tab-item} Codex
:sync: codex

`bearer_token_env_var` names the environment variable that holds the token.

<!-- check: skip -->
```toml
[mcp_servers.plone-blog]
url = "http://127.0.0.1:8000/mcp"
bearer_token_env_var = "PLONE_MCP_TOKEN"
```
:::

:::{tab-item} Gemini CLI
:sync: google

<!-- check: skip -->
```shell
gemini mcp add --transport http --header "Authorization: Bearer $TOKEN" plone-blog http://127.0.0.1:8000/mcp
```
:::
::::

(howto-assistant-python)=

### Connect from Python

The `mcp` package has a client, for a program of your own.

<!-- check: file client.py -->
```python
import asyncio
import os

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

URL = "http://127.0.0.1:8000/mcp"


async def main() -> None:
    headers = {"Authorization": f"Bearer {os.environ['TOKEN']}"}
    async with httpx2.AsyncClient(headers=headers) as http:
        async with Client(streamable_http_client(URL, http_client=http)) as client:
            tools = await client.list_tools()
            print(len(tools.tools) > 0)
            result = await client.call_tool("site_info", {})
            print(result.content[0].text)


asyncio.run(main())
```

```shell
python client.py
```

```text
True
{
  "url": "http://localhost:8080/Plone",
  "authenticated": true,
  "username": "admin",
  "credentials_rejected": false,
  "read_only": false,
  "plone_version": "6.1.5",
  "frontend_url": "http://localhost:3000",
  "dry_run": false
}
```

To start a server on your computer instead, pass `StdioServerParameters(command="plone-client", args=["mcp", "--profile", "blog"])` from the `mcp` package to `Client`.

Stop the server when you are done.

```shell
kill "$SERVER"
```

<!-- check: stop -->

To reach the server from another machine, listen on another address with `--host`, and put a proxy that adds TLS in front of it.

### Run the server in a container

The Compose file has an `mcp` service that serves the sample site over HTTP.
It takes the token from `PLONE_CLIENT_MCP_TOKEN`, and it starts only when you ask for its profile.

<!-- check: skip -->
```shell
export PLONE_CLIENT_MCP_TOKEN=$(openssl rand -hex 32)
docker compose --profile mcp up --wait
```

The server listens on `http://127.0.0.1:8000/mcp`, a few seconds after the command returns, because the container installs plone-client when it starts.
Set `MCP_PORT` to use another port.
Outside this sample, set the token the same way in any container, where there is no keyring.

## Related

- {ref}`reference-assistant-server` lists the tools and their arguments.
- {ref}`howto-protect` decides what an assistant can see and do.
- {ref}`explanation-interfaces` compares the MCP server with the command line and the agent skill.
- {ref}`howto-agents` sets up a coding agent with the command line instead.
- {ref}`howto-troubleshoot` helps when a client cannot see the server or a tool.
