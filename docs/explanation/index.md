---
myst:
  html_meta:
    "description": "Background on plone-client: its design, how it handles secrets, and how it serves agents and assistants through the command line and an MCP server."
    "property=og:description": "Background on plone-client: its design, how it handles secrets, and how it serves agents and assistants through the command line and an MCP server."
    "property=og:title": "Explanation"
---

(explanation-index)=

# Explanation

Understand why plone-client works the way it does.

```{toctree}
:maxdepth: 1
:hidden: true

design
secrets
cli-for-agents
interfaces
when-to-call-the-api-directly
```

`````{grid} 1 1 2 2
:gutter: 3

````{grid-item-card} 🏗️ Design
:link: design
:link-type: doc

One client per site, and retries that never repeat a change.
````

````{grid-item-card} 🔐 Secrets
:link: secrets
:link-type: doc

Why secrets stay out of the configuration file.
````

````{grid-item-card} 🤖 A command line for agents
:link: cli-for-agents
:link-type: doc

What makes a command line good for an agent.
````

````{grid-item-card} 🧭 Interfaces
:link: interfaces
:link-type: doc

The library, the command line, the skill, and the MCP server.
````

````{grid-item-card} 🔀 When to call the API directly
:link: when-to-call-the-api-directly
:link-type: doc

Managers, generic requests, and plain `plone.restapi`.
````
`````
