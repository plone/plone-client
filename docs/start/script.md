---
myst:
  html_meta:
    "description": "The path for Python developers: read a Plone site in five lines, then follow the steps to a script that keeps a site in sync."
    "property=og:description": "The path for Python developers: read a Plone site in five lines, then follow the steps to a script that keeps a site in sync."
    "property=og:title": "Script Plone from Python"
---

(start-script)=

# Script Plone from Python

At the end of this path, you will have a Python script that keeps content on a {term}`Plone` site in step with a data file, previews its changes, and handles errors.

## Try it now

This script reads [`demo.plone.org`](https://demo.plone.org), a public site that resets every night, without logging in.

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

## You need

- Python 3.11 or later, and [uv](https://docs.astral.sh/uv/).
- [Docker](https://www.docker.com/), from the second step on.
- No Plone knowledge: {doc}`index` has what you need.

## Follow these steps

1. {ref}`howto-install` adds plone-client to your project, because the rest of the path needs it.
2. {ref}`tutorial-first-script` is the core of the path: you read a site, change it, and end with a sync from a JSON file.
3. {ref}`reference-content-model` shows what your script reads and writes, so that your fields and blocks land where you expect.
4. {ref}`howto-handle-errors` turns the failures of a real site into code paths.
5. {ref}`howto-sync` takes the tutorial's script to production.
6. {ref}`tutorial-migrate` applies the same ideas to two sites.

## Going further

- {ref}`reference-services` has an example for every service.
- {ref}`reference-blocks` builds the blocks of a page in Python.
- {ref}`reference-exceptions` lists the exception for each kind of failure.
- {ref}`howto-large-sites` keeps scripts fast on large sites.
- {ref}`explanation-direct-api` says when to step outside the {term}`managers <manager>`.

## If something breaks

{ref}`howto-troubleshoot` goes from the symptom to the fix.

## Before you connect a real site

- Log in as a dedicated Plone user with only the permissions the script needs, not `admin`.
- Start with `read_only=True`, which refuses every change before sending it.
- Pass `dry_run=True` on the first run that writes, and read `client.dry_run_log`; see {ref}`howto-preview-changes`.
- Keep the password out of the script: use a {term}`profile`, or an environment variable with {meth}`~plone_client.PloneClient.from_env`; see {ref}`howto-scripts-ci`.
- Catch the exceptions of {ref}`reference-exceptions`, so that a refused change stops the script instead of half-applying it.
