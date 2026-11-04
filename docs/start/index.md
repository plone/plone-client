---
myst:
  html_meta:
    "description": "What plone-client is, for someone who knows Python or a shell but not Plone: the concepts, what each interface can do, and the two sites you can practice on."
    "property=og:description": "What plone-client is, for someone who knows Python or a shell but not Plone: the concepts, what each interface can do, and the two sites you can practice on."
    "property=og:title": "Get started"
---

(start-index)=

# Get started

By the end of this page, you will know what plone-client does, the few Plone words the rest of this documentation uses, and which path to follow.
You need to know Python or a shell, and nothing about Plone.

```{toctree}
:maxdepth: 1
:hidden: true

script
cli
agents
```

```{warning}
plone-client is in alpha.
Its Python API and its commands can change between releases; read the {doc}`/changelog` before you upgrade.
```

## What plone-client is

plone-client is one library with three ways in.
The Python library talks to a site, the command line wraps the library for terminals and scripts, and the {term}`MCP` server wraps it for AI assistants.
All three use the same {term}`profiles <profile>` and the same safety switches.

## Plone in six words

Plone
: A content management system. {term}`Plone` stores content and decides who can see and change it.

Volto
: The website people see and edit. {term}`Volto` is a React application that runs in front of Plone.

`plone.restapi`
: The JSON API of Plone. Everything plone-client does goes through {term}`plone.restapi`, so whatever you can do with plone-client, the API allows, and with the same permissions.

Content type
: The kind of an item, such as a page or a news item. A {term}`content type` decides which fields the item has.

Workflow
: The life of an item, such as `private` then `published`. A {term}`workflow` decides who can see the item in each state, and a {term}`transition` moves it from one state to the next.

Block
: A piece of a page, such as a paragraph or an image. A Volto page is a list of {term}`blocks <block>`, stored as JSON on the item.

And one word of plone-client: a {term}`profile` is a site with a name, such as `production`, whose password stays in your {term}`keyring`.

The {doc}`/glossary` defines every other term.

## What each interface can do

<!-- source: src/plone_client/managers, src/plone_client/cli, docs/_generated/mcp-tools.md -->

| You want to | Library | Command line | MCP server |
|---|---|---|---|
| {ref}`Read, search, and list content <reference-service-search>` | Yes | Yes | Yes |
| {ref}`Create, change, move, copy, and delete content <reference-service-content>` | Yes | Yes | Yes |
| {ref}`Run workflow transitions <reference-service-workflow>` | Yes | Yes | Yes |
| {ref}`Create a page from Markdown or HTML <reference-blocks>` | Yes | Yes | Yes |
| {ref}`Create an item with files and a lead image <reference-service-files>` | Yes | Yes | Yes |
| {ref}`Upload a folder of documents <reference-service-files>` | Yes | Yes | Yes |
| {ref}`Edit single blocks of a page <reference-blocks>` | Yes, with {mod}`plone_client.blocks` | With `update` | Yes |
| {ref}`List the block types of a site <reference-blocks>` | Yes | Yes | Yes |
| {ref}`Manage users and groups <reference-service-people>` | Yes | Yes | With `call_service` |
| {ref}`Change the registry and control panels <reference-service-site>` | Yes | Registry; the rest with `request` | With `call_service` |
| {ref}`Call any other service <reference-services>` | Yes | With `request` | With `call_service` |
| Use several sites at once | One client per site | One profile per command | One server |
| {ref}`Refuse changes, or preview them <howto-preview-changes>` | Yes | Yes | Yes |

*Yes* means a dedicated method, command, or {term}`tool <tool>`.
*With `request`* and *with `call_service`* mean the generic request: it reaches the same service with the same permissions, but you write the path and the body yourself.
Every cell is bounded by the permissions of the Plone user you log in as, and by the `plone.restapi` version of the site; see {ref}`reference-compatibility`.

## Two sites you can use

You can practice on two sites.

[`demo.plone.org`](https://demo.plone.org)
: A public site with nothing to install.
  It is shared with other visitors and resets every night, so this documentation only reads from it.

Your own, in Docker
: A {term}`Compose site` with Volto and sample content, which takes about a minute to start.
  Every tutorial step that changes something uses it; see {ref}`howto-run-a-site`.

## Which versions work

plone-client works with Plone 6.0, 6.1, and 6.2, and needs Python 3.11 or later.
{ref}`reference-compatibility` lists the details.

## Pick your path

`````{grid} 1 1 3 3
:gutter: 3

````{grid-item-card} 🐍 Script Plone from Python
:link: script
:link-type: doc

You want code that reads or changes a site.
````

````{grid-item-card} 💻 Manage sites from a terminal
:link: cli
:link-type: doc

You want commands that you type, or put in a script.
````

````{grid-item-card} 🤖 Work with AI assistants
:link: agents
:link-type: doc

You want a model to do the editing, within limits.
````
`````
