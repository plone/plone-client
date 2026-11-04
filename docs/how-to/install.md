---
myst:
  html_meta:
    "description": "Install plone-client as a library in a Python project, or as a command line tool."
    "property=og:description": "Install plone-client as a library in a Python project, or as a command line tool."
    "property=og:title": "Install plone-client"
---

(howto-install)=

# Install plone-client

This guide shows you how to install plone-client, as a library for your own code, as a command line tool, or both.
plone-client needs Python 3.11 or later.

## Use it as a library

Add it to your project's dependencies.
The library needs only [httpx](https://www.python-httpx.org).

::::{tab-set}
:sync-group: installer

:::{tab-item} uv
:sync: uv

```shell
uv add plone-client
```
:::

:::{tab-item} pip
:sync: pip

```shell
pip install plone-client
```
:::
::::

## Use the command line

Install it as a tool, with the `cli` extra, which adds `typer`, `keyring`, and `tomlkit`.

::::{tab-set}
:sync-group: installer

:::{tab-item} uv
:sync: uv

```shell
uv tool install "plone-client[cli]"
```
:::

:::{tab-item} pipx
:sync: pip

```shell
pipx install "plone-client[cli]"
```
:::
::::

Check that it works.

```shell
plone-client --version
```

To complete commands in your shell, run `plone-client --install-completion`.

## Add the optional features

Two more extras add optional features.
This table shows what each part needs.

<!-- source: pyproject.toml requires-python and [project.optional-dependencies]; src/plone_client/blocks.py _converter -->

| Install | Adds | Python |
|---|---|---|
| `plone-client` | The library. | 3.11 or later |
| `plone-client[cli]` | The command line. | 3.11 or later |
| `plone-client[mcp]` | The MCP server, `plone-client mcp`, with the command line it runs in. | 3.11 or later |
| `plone-client[markdown]` | Pages from Markdown or HTML, converted to blocks by `collective.html2blocks`. | 3.12 or later |

On Python 3.11, the `markdown` extra installs nothing.
`create-page`, `upload-tree --pages`, the `create_page` tool, and Markdown in {mod}`plone_client.blocks` then raise {class}`~plone_client.exceptions.PloneConfigurationError`, which names the fix.
{ref}`tutorial-first-agent-session` and {ref}`tutorial-editorial-assistant` need the extra, so they need Python 3.12.

Combine extras as you need them.

```shell
uv tool install "plone-client[mcp,markdown]"
```

## Use both

If your code reads the {term}`profiles <profile>` of the command line with {meth}`~plone_client.PloneClient.from_profile`, add the extra to your project's dependencies too.

```shell
uv add "plone-client[cli]"
```

## Next steps

- {ref}`howto-connect` connects your code to a site.
- {ref}`howto-profiles` adds your sites as profiles.
- {ref}`reference-compatibility` lists the Plone versions that work.
