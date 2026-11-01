---
myst:
  html_meta:
    "description": "Reference documentation of plone-client: services, compatibility, the client, operations, blocks, command line, MCP server, configuration, and exceptions."
    "property=og:description": "Reference documentation of plone-client: services, compatibility, the client, operations, blocks, command line, MCP server, configuration, and exceptions."
    "property=og:title": "Reference"
---

(reference-index)=

# Reference

Look up the facts: which versions of Plone work, what each parameter, command, and setting does, and what each error means.

```{toctree}
:maxdepth: 1
:hidden: true

services/index
client
managers
operations
blocks
content-model
python-api
javascript-client
cli
cheat-sheet
mcp-server
skill
compatibility
configuration
exceptions
/changelog
```

## Python library

`````{grid} 1 1 2 2
:gutter: 3

````{grid-item-card} 🌐 Services
:link: services/index
:link-type: doc

Every service, with Python, command line, and HTTP examples.
````

````{grid-item-card} 🔧 The client
:link: client
:link-type: doc

`PloneClient`: parameters and generic requests.
````

````{grid-item-card} 🗃️ Managers
:link: managers
:link-type: doc

One manager per service, and every way to name an item.
````

````{grid-item-card} ⚡ Operations
:link: operations
:link-type: doc

Tasks of several requests, and their results.
````

````{grid-item-card} 🧱 Block helpers
:link: blocks
:link-type: doc

Build, walk, and check Volto blocks.
````

````{grid-item-card} 📐 Content model
:link: content-model
:link-type: doc

How the content of a site is shaped.
````

````{grid-item-card} 🐍 Python API
:link: python-api
:link-type: doc

Authentication, profiles, credentials, and utilities.
````

````{grid-item-card} 🟨 JavaScript client map
:link: javascript-client
:link-type: doc

`@plone/client` functions and their Python equals.
````
`````

## Command line and agents

`````{grid} 1 1 2 2
:gutter: 3

````{grid-item-card} 💻 Command line
:link: cli
:link-type: doc

Every command, with its arguments and options.
````

````{grid-item-card} 📝 Cheat sheet
:link: cheat-sheet
:link-type: doc

Commands by task, on one page.
````

````{grid-item-card} 🤖 MCP server
:link: mcp-server
:link-type: doc

Tools, resources, modes, and errors.
````

````{grid-item-card} 🎓 Agent skill
:link: skill
:link-type: doc

What the skill tells an agent, and where it lives.
````
`````

## Everything else

`````{grid} 1 1 2 2
:gutter: 3

````{grid-item-card} 🧮 Compatibility
:link: compatibility
:link-type: doc

Plone and `plone.restapi` versions.
````

````{grid-item-card} ⚙️ Configuration
:link: configuration
:link-type: doc

Files, environment variables, and profile keys.
````

````{grid-item-card} 🚨 Exceptions
:link: exceptions
:link-type: doc

Errors, statuses, and exit codes.
````

````{grid-item-card} 📜 Changelog
:link: /changelog
:link-type: doc

What changed in each release.
````
`````
