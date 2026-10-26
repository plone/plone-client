---
myst:
  html_meta:
    "description": "plone-client is a Python library and command line client for Plone sites, built on plone.restapi."
    "property=og:description": "plone-client is a Python library and command line client for Plone sites, built on plone.restapi."
    "property=og:title": "plone-client"
    "keywords": "Plone, plone.restapi, client, command line, CLI, Python, agents"
---

# plone-client

plone-client is a Python library and a command line client for [Plone](https://plone.org) sites, built on [`plone.restapi`](https://6.docs.plone.org/plone.restapi/docs/source/index.html).

As a library, it gives your code a client with one manager per REST API service.
Use it to sync content from an external source, to migrate content, or to automate site maintenance.

```python
from plone_client import PloneClient

with PloneClient.from_profile("production") as client:
    for item in client.search.iter("/news", portal_type="News Item", review_state="published"):
        print(item["@id"], item["title"])
```

As a command line client, it manages any number of Plone sites, each one a named profile whose password stays in your operating system's keyring.
It prints JSON and uses stable exit codes, so shell scripts and coding agents can use it as well as people.

```shell
plone-client -p production ls /news -f @id,title,review_state
```

It works with Plone 6.0, 6.1, and 6.2; see {ref}`reference-compatibility`.

## Where to go next

`````{grid} 1 1 2 2
:gutter: 3

````{grid-item-card} Tutorials
:link: tutorials/index
:link-type: doc

New to plone-client?
Write your first script, or run your first command line session, against a Plone site in Docker.
````

````{grid-item-card} How-to guides
:link: how-to/index
:link-type: doc

Solve a specific problem: connect to a site, manage profiles, sync content, upload files, or set up a coding agent.
````

````{grid-item-card} Reference
:link: reference/index
:link-type: doc

Look something up: compatibility with Plone and plone.restapi, the client and its managers, commands, configuration, and errors.
````

````{grid-item-card} Explanation
:link: explanation/index
:link-type: doc

Understand the design: one client per site, retries that never repeat a change, secrets outside the configuration file.
````
`````

```{toctree}
:hidden:
:maxdepth: 2

tutorials/index
how-to/index
reference/index
explanation/index
```
