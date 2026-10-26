<p align="center">
    <img alt="Plone Logo" width="200px" src="https://raw.githubusercontent.com/plone/.github/main/plone-logo.png">
</p>

<h1 align="center">plone-client</h1>

<div align="center">

[![PyPI](https://img.shields.io/pypi/v/plone-client)](https://pypi.org/project/plone-client/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/plone-client)](https://pypi.org/project/plone-client/)
[![PyPI - License](https://img.shields.io/pypi/l/plone-client)](https://pypi.org/project/plone-client/)
[![CI](https://github.com/plone/plone-client/actions/workflows/ci.yml/badge.svg)](https://github.com/plone/plone-client/actions/workflows/ci.yml)

**A Python library and command line client for Plone sites, built on plone.restapi.**

</div>

## What it does

- **As a library**, plone-client gives your code a client with one manager per `plone.restapi` service.
  Use it to sync content from an external source, to migrate content, or to automate site maintenance.
- **As a command line client**, `plone-client` manages any number of Plone sites, each one a named profile whose password stays in your operating system's keyring.
  It prints JSON and uses stable exit codes, so shell scripts and coding agents can use it as well as people.

It works with Plone 6.0, 6.1, and 6.2, and needs Python 3.11 or later.
See the [compatibility grid](https://plone.github.io/plone-client/reference/compatibility.html) for the `plone.restapi` versions.

## Install

```shell
uv add plone-client                    # the library
uv tool install "plone-client[cli]"    # the command line
```

## Use the library

```python
from plone_client import PloneClient
from plone_client import blocks

with PloneClient("https://example.org", username="editor", password="secret") as client:
    page = client.content.create(
        "/news",
        "Document",
        title="Hello, Plone",
        **blocks.build(blocks.title(), blocks.description(), blocks.text("It works.")),
    )
    client.workflow.transition(page["@id"], "publish")

    for item in client.search.iter("/news", portal_type="Document", review_state="published"):
        print(item["@id"], item["title"])
```

## Use the command line

```shell
plone-client profile add prod --url https://example.org --username editor --read-only
plone-client -p prod ls /news -f @id,title,review_state
plone-client -p prod search -t "News Item" --state published --limit 10
```

## Documentation

The documentation is at <https://plone.github.io/plone-client>.

- [Tutorials](https://plone.github.io/plone-client/tutorials/index.html): your first script and your first command line session.
- [How-to guides](https://plone.github.io/plone-client/how-to/index.html): sync content, manage profiles, upload files, use it from coding agents.
- [Reference](https://plone.github.io/plone-client/reference/index.html): compatibility, the client, managers, commands, configuration, and errors.
- [Explanation](https://plone.github.io/plone-client/explanation/index.html): the design, secrets, and why a command line suits agents.

## Contribute

- [Issue tracker](https://github.com/plone/plone-client/issues)
- [Source code](https://github.com/plone/plone-client)
- [Contributing guide](https://github.com/plone/plone-client/blob/main/CONTRIBUTING.md)

## License

The project is licensed under the GPLv2.
See [LICENSE.GPL](https://github.com/plone/plone-client/blob/main/LICENSE.GPL).
