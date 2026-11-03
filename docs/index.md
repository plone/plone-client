---
myst:
  html_meta:
    "description": "plone-client automates Plone sites from Python, from a terminal, or through an AI assistant, on top of plone.restapi."
    "property=og:description": "plone-client automates Plone sites from Python, from a terminal, or through an AI assistant, on top of plone.restapi."
    "property=og:title": "plone-client"
    "keywords": "Plone, plone.restapi, client, command line, CLI, Python, agents, MCP"
---

# plone-client

One client to automate Plone, whether the operator is a developer, a shell script, or an AI agent.

plone-client is a Python library, a command line, and an {term}`MCP` server for [Plone](https://plone.org) sites, built on [`plone.restapi`](https://6.docs.plone.org/plone.restapi/docs/source/index.html).

```{admonition} Alpha
:class: warning
plone-client is in alpha: its Python API and its commands can change before 1.0.
Read the {doc}`changelog` before you upgrade.
```

## Try it now

You need only [uv](https://docs.astral.sh/uv/).
This command lists the top of [`demo.plone.org`](https://demo.plone.org), a public site that anyone can use and that resets every night.

<!-- check: start -->
<!-- check: demo -->
```shell
uvx --from "plone-client[cli]" plone-client --url https://demo.plone.org ls / -f title,review_state
```

```json
[
  {
    "title": "Plone Foundation Logo",
    "review_state": null
  },
  {
    "title": "Images",
    "review_state": "published"
  },
  {
    "title": "Blocks",
    "review_state": "published"
  },
  {
    "title": "Content Types",
    "review_state": "published"
  },
  {
    "title": "Vertical Spacing",
    "review_state": "published"
  }
]
```

<!-- check: stop -->

## Pick your path

`````{grid} 1 1 3 3
:gutter: 3

````{grid-item-card} 🐍 Script Plone from Python
:link: start/script
:link-type: doc

Sync content from another system, migrate a site, or automate maintenance.
````

````{grid-item-card} 💻 Manage sites from a terminal
:link: start/cli
:link-type: doc

Work on many sites by name, preview every change, and script the rest.
````

````{grid-item-card} 🤖 Work with AI assistants
:link: start/agents
:link-type: doc

Let an assistant or a coding agent edit a site, within limits you set.
````
`````

New to Plone?
{doc}`start/index` explains what you need to know, in terms of what you already know.

## Install

::::{tab-set}
:sync-group: installer

:::{tab-item} uv
:sync: uv

```shell
uv add plone-client                            # Python library
uv tool install "plone-client[cli]"            # command line
uv tool install "plone-client[mcp,markdown]"   # assistants
```
:::

:::{tab-item} pip and pipx
:sync: pip

```shell
pip install plone-client                       # Python library
pipx install "plone-client[cli]"               # command line
pipx install "plone-client[mcp,markdown]"      # assistants
```
:::
::::

plone-client needs Python 3.11 or later, and the `markdown` extra needs 3.12; see {ref}`howto-install`.

## What it looks like

::::{tab-set}
:sync-group: door

:::{tab-item} Python library
:sync: python

Save this as `demo.py`; it reads the public demo site without logging in.

<!-- check: start -->
<!-- check: file demo.py -->
```python
from plone_client import PloneClient

with PloneClient("https://demo.plone.org") as site:
    for item in site.search.iter(portal_type="Document", limit=3):
        print(item["title"])
```

<!-- check: demo -->
```shell
uv run --with plone-client demo.py
```

<!-- check: stop -->

With a {term}`profile`, replace the URL with `PloneClient.from_profile("production")`.
:::

:::{tab-item} Command line
:sync: terminal

Preview publishing a folder and everything in it, on the public demo site.
With `-n`, the command prints the request it would send, and sends nothing.

<!-- check: start -->
<!-- check: demo -->
```shell
uvx --from "plone-client[cli]" plone-client --url https://demo.plone.org -n workflow /content-types publish --recursive
```

```json
{
  "dry_run": true,
  "method": "POST",
  "url": "https://demo.plone.org/++api++/content-types/@workflow/publish",
  "json": {
    "include_children": true
  }
}
```

<!-- check: stop -->

On your own site, name its {term}`profile` instead of the URL.

```shell
plone-client -n -p production workflow /news publish --recursive
```
:::

:::{tab-item} Assistants
:sync: agents

Add a site as a {term}`profile`, and give your assistant this server.
This is the `mcpServers` shape that Claude Desktop, Cursor, and most clients read; VS Code names the key `servers`, as {ref}`howto-assistant` shows.

```json
{
  "mcpServers": {
    "plone": {
      "command": "plone-client",
      "args": ["--profile", "production", "--read-only", "mcp"]
    }
  }
}
```

Then ask it: "Which news items on the site are still private?"
:::
::::

## Safe by design

- **Secrets stay out of files.** A {term}`profile` keeps its password in the {term}`keyring` of your operating system, or reads it from the environment or a command where there is no keyring; see {ref}`howto-scripts-ci`.
- **Read-only sites stay read-only.** A profile or a client can refuse every change before sending it.
- **Dry runs show the plan.** `-n` and `dry_run=True` print the requests and send none of them.
- **Destructive commands ask first.** Without a terminal, they need `--yes`.
- **Failures have names.** Each kind of failure has its own exception and {term}`exit code`, listed in {ref}`reference-exceptions`.
- **Plone has the last word.** Every request runs with the permissions of the user you logged in as.

{doc}`how-to/protect-a-site-from-an-agent` puts these together for assistants.

## All the documentation

`````{grid} 1 2 4 4
:gutter: 3

````{grid-item-card} 🚀 Tutorials
:link: tutorials/index
:link-type: doc

Learn by doing, one step at a time.
````

````{grid-item-card} 🧭 How-to guides
:link: how-to/index
:link-type: doc

Solve a specific problem.
````

````{grid-item-card} 📖 Reference
:link: reference/index
:link-type: doc

Look up every service, command, and setting.
````

````{grid-item-card} 💡 Explanation
:link: explanation/index
:link-type: doc

Understand why it works this way.
````
`````

```{toctree}
:hidden:
:maxdepth: 2

start/index
tutorials/index
how-to/index
reference/index
explanation/index
glossary
```
