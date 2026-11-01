---
myst:
  html_meta:
    "description": "The terms used in the plone-client documentation, from Plone concepts to agents and profiles."
    "property=og:description": "The terms used in the plone-client documentation, from Plone concepts to agents and profiles."
    "property=og:title": "Glossary"
---

(glossary)=

# Glossary

The terms this documentation uses, each defined once.

## Plone

```{glossary}
Plone
  An open source content management system written in Python.
  plone-client works with Plone 6; see {ref}`reference-compatibility`.

Volto
  The React frontend of Plone 6, which edits pages as {term}`blocks <block>`.
  It runs as a separate server in front of the Plone backend.

Classic UI
  The server-rendered interface of Plone, an alternative to {term}`Volto`.
  A Classic UI site stores text in fields, not in blocks.

plone.restapi
  The add-on that ships with Plone and exposes its content and settings as a JSON API.
  Everything plone-client does goes through it, or through a service of the {term}`Volto` server.

++api++
  A segment in a URL that sends the request to `plone.restapi`, as in `https://example.org/++api++/news`.
  plone-client adds it for you, and removes it from the URLs it reads.

site root
  The top of a Plone site, path `/` in plone-client.
  On a backend without a frontend, its URL ends in the site id, as in `http://localhost:8080/Plone`.

content item
  One thing stored in a site, such as a page, a news item, or an image.
  Each has a path, a {term}`UID`, and a {term}`content type`.

content type
  The kind of a {term}`content item`, which decides its fields.
  `plone.restapi` calls its id `@type`, and the catalog calls it `portal_type`.

portal_type
  The id of a {term}`content type`, such as `Document` or `News Item`.

folderish
  Said of a {term}`content item` that can hold others.
  On a {term}`Volto` site, a `Document` is folderish, and the `Folder` type usually cannot be added.

block
  One piece of a page on a {term}`Volto` site, such as a paragraph, an image, or a grid.
  A block is a JSON object with an `@type`, stored in the `blocks` field of its item.

blocks_layout
  The field of a {term}`content item` that lists the ids of its {term}`blocks <block>` in display order.

slate
  The rich text {term}`block` of {term}`Volto`, and the JSON format of its value.

lead image
  The picture that represents an item in listings.
  On a {term}`Volto` site it is `preview_image_link`, a relation to an Image; on other sites it is an `image` field.
  See {ref}`reference-content-model`.

workflow
  The states a {term}`content item` goes through, such as `private` and `published`, and who can see it in each.

transition
  A step from one {term}`workflow` state to another, such as `publish` or `retract`.

review_state
  The name of the {term}`workflow` state a {term}`content item` is in.

UID
  The unique id of a {term}`content item`, which stays the same when the item moves.

resolveuid
  A link form that points to a {term}`UID` and not to a path, so that it survives moves.
```

## plone-client

```{glossary}
ref
  How you name an item in plone-client: a path, a URL inside the site, `uid:<UID>`, or a {term}`resolveuid` link.
  See {ref}`reference-managers`.

manager
  An attribute of `PloneClient` that groups the calls to one service, such as `client.content`.
  See {ref}`reference-services`.

operation
  A task of several requests in the right order, such as creating a page with its images.
  See {ref}`reference-operations`.

profile
  A named site in the configuration file: its URL, its user, and where its secret is.
  See {ref}`howto-profiles`.

group
  A name for several {term}`profiles <profile>`, which the {term}`MCP` server can serve together.

keyring
  The password store of your operating system, such as the macOS Keychain.
  plone-client keeps the secrets of {term}`profiles <profile>` there by default.

secret
  The password or token of a {term}`profile`.

read-only
  A mode of a client or a {term}`profile` that refuses every change before sending it.

dry run
  A mode that does not send changes, and shows what it would have sent.
  Compare it with {term}`read-only` in {ref}`howto-preview-changes`.

confirmation
  The question destructive commands ask before they run, which `--yes` answers in advance.

exit code
  The number a command returns to the shell.
  plone-client gives each kind of failure its own; see {ref}`reference-cli`.

frontend_url
  The address of the {term}`Volto` server of a site, which plone-client needs to ask it which blocks the site has.

demo site
  `https://demo.plone.org`, a public Plone site that anyone can use and that resets every night.

Compose site
  The Plone site with {term}`Volto` and sample content that the `docker-compose.yml` of this repository starts on your computer.
  See {ref}`howto-run-a-site`.
```

## Assistants and agents

```{glossary}
assistant
  A chat application backed by a language model, such as Claude Desktop, which uses tools through {term}`MCP`.

coding agent
  A language model that runs commands in a terminal or an editor, such as Claude Code, Codex, or Cursor.

skill
  A file that teaches a {term}`coding agent` how to use a tool.
  See {ref}`reference-skill`.

MCP
  The Model Context Protocol, a standard way to offer {term}`tools <tool>` and {term}`resources <resource>` to a language model.

tool
  A function that an {term}`MCP` server offers and that a model can call.

resource
  Data that an {term}`MCP` server offers at a URI, which the application reads and gives to the model.

instructions
  The text an {term}`MCP` server sends its clients, which explains to the model how to use it.
```
