# plone-client

A Python library and a command line client for [Plone](https://plone.org) sites, built on [plone.restapi](https://6.docs.plone.org/plone.restapi/).

As a library, it gives scripts and applications a typed, synchronous client with one manager per REST API service.
Use it to sync content from an external source into Plone, to migrate content, or to automate site maintenance.

As a command line client, `plone-client` manages content on any number of Plone sites.
Each site is a named profile, and its secret stays in the operating system's keyring.
It prints JSON and uses stable exit codes, so coding agents and shell scripts can use it in place of an MCP server.

It works with Plone 6.0 and 6.1, and needs Python 3.11 or later.

## Installation

The library needs only [httpx](https://www.python-httpx.org).

```shell
uv add plone-client
```

The command line client needs the `cli` extra, which adds Typer, keyring and tomlkit.

```shell
uv tool install "plone-client[cli]"
```

```{toctree}
:maxdepth: 2
:caption: Guides

library
sync
cli
profiles
agents
migrating
```

```{toctree}
:maxdepth: 1
:caption: Reference

reference
changelog
```
