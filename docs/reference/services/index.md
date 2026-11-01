---
myst:
  html_meta:
    "description": "Every service plone-client implements, with Python, command line, and HTTP examples and real answers."
    "property=og:description": "Every service plone-client implements, with Python, command line, and HTTP examples and real answers."
    "property=og:title": "Services"
---

(reference-services)=

# Services

Every service that plone-client implements, with an example in Python, on the command line, and in HTTP, and the answer of a real site.

(reference-services-reading)=

## How to read these pages

Every example on these pages ran against a real site, and each answer is what that site returned.
The same idea drives the documentation of `plone.restapi`, whose tests write its examples.

The site is the {term}`Compose site` described in {ref}`howto-run-a-site`, and the examples run in order.
Each one uses a client like this.

```python
from plone_client import PloneClient

client = PloneClient(
    "http://localhost:8080/Plone",
    username="admin",
    password="admin",
    frontend_url="http://localhost:3000",
)
```

Each method has up to three tabs, which stay in step when you switch one of them.

Python
: The call, with the answer below the tabs.
  A sentence under the answer says what it leaves out, to keep it short.

Command line
: The `plone-client` command for the same job, when there is one, with its output.

HTTP
: Every request the client sent, and the same request as a `curl` command.

An example that could not run says why, and shows the request that the client would send.

```{toctree}
:maxdepth: 1
:hidden: true

content
search
workflow
files
navigation
related-content
people
types
site
```

`````{grid} 1 1 2 2
:gutter: 3

````{grid-item-card} 📄 Content
:link: content
:link-type: doc

`client.content`: read, create, update, delete, copy, move, order, and lock items.
````

````{grid-item-card} 🔎 Search
:link: search
:link-type: doc

`client.search` and `client.querystring`: find items in the catalog.
````

````{grid-item-card} 🔁 Workflow and history
:link: workflow
:link-type: doc

`client.workflow`, `client.history`, and `client.working_copy`.
````

````{grid-item-card} 📎 Files
:link: files
:link-type: doc

`client.files`: upload, replace, and download files and images.
````

````{grid-item-card} 🧭 Navigation
:link: navigation
:link-type: doc

`client.navigation`: menus, breadcrumbs, and actions.
````

````{grid-item-card} 🔗 Comments, aliases, relations, and translations
:link: related-content
:link-type: doc

`client.comments`, `client.aliases`, `client.relations`, and `client.translations`.
````

````{grid-item-card} 👥 Users, groups, and sharing
:link: people
:link-type: doc

`client.users`, `client.groups`, and `client.sharing`.
````

````{grid-item-card} 🧩 Types and vocabularies
:link: types
:link-type: doc

`client.types`, `client.block_types`, and `client.vocabularies`.
````

````{grid-item-card} 🛠️ Site settings
:link: site
:link-type: doc

`client.registry`, `client.controlpanels`, `client.addons`, `client.content_rules`, and `client.system`.
````
`````
