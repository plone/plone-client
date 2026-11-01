---
name: plone-client
description: Read and change content on a Plone site with the plone-client command line — list, search, create, update, publish, upload, and delete items, write Volto pages and blocks, manage users and groups, and call any plone.restapi service. Use when the user asks to work with a Plone site's content or configuration, or mentions plone-client, plone.restapi, Volto content, or a Plone profile.
---

# plone-client

`plone-client` talks to a Plone site through `plone.restapi`.
Results are JSON on standard output; errors are JSON on standard error with a meaningful exit code.

## Rules

- Never ask for passwords and never call the REST API with `curl`.
  The profiles already hold the credentials, in the system keyring.
- Never create, change, or remove profiles unless the user asks; run `plone-client profile list` to see which exist.
- Before changing a site other than a local one, run the command with `-n` (dry run) and show the user the requests it would send.
- Never pass `--yes` to `delete`, `users delete`, or `groups delete` unless the user confirmed the exact items.
- Exit code 7 means the profile is read-only. Do not work around it; tell the user.
- A dry run shows the request, not the site's answer, so a request that passes `-n` can still be refused.
- Use `-f` to keep only the keys you need, so the output stays small.
- Read the `@id` of what a command creates: the site may change the id you asked for (`/blocks` became `/blocks-1`).
- After a change that matters, read the item back: a success does not prove that every field was stored.

## Choosing the site

The profile comes from, in order: `-p <name>`, `$PLONE_CLIENT_PROFILE`, a `.plone-client.toml` file (`profile = "<name>"`) in the working directory or a parent, and the current profile.

```shell
plone-client profile list          # profiles and which one is current
plone-client info                  # site, user, and Plone version
plone-client -p production get /   # one command against another profile
```

## Items

`<ref>` is a path (`/news/item`), a URL inside the site, `uid:<UID>`, or a `resolveuid` link.

```shell
plone-client get /news/item -f @id,title,review_state
plone-client ls /news -f @id,title,review_state
plone-client search /news -q "keyword" -t "News Item" --state published --limit 10 -f @id,title
plone-client search -i Subject=plone --count
plone-client resolve uid:0123456789abcdef
plone-client history /news/item
plone-client sharing /news/item
```

## Changes

`create` and `update` take field values from `-d` (JSON object, `@file.json`, or `-` for stdin), then `-s` (repeatable: `key=text` for a string, `key:=json` for any JSON value), then `--title` and `--description`; later ones win.

```shell
plone-client create /news "News Item" --title "Title" --description "Summary" --publish publish
plone-client update /news/item -s subjects:='["plone", "release"]'
plone-client update /news/item -d @fields.json
plone-client workflow /news/item                  # state and available transitions
plone-client workflow /news/item publish
plone-client workflow /news publish --recursive
plone-client copy /news/item --to /archive
plone-client move /news/old --to /archive
plone-client order /news item top
plone-client delete /news/old --yes               # only after the user confirmed
plone-client upload /news/item photo.jpg report.pdf
plone-client download /news/item/photo.jpg
```

Commands that change an item print `@id`, `@type`, `UID`, `id`, `title`, and `review_state`; add `--full` for the whole item.

## Tasks of several steps

These commands send several requests in the right order and print every one of them, with what they created.
If one stops part way, its error has a `result` with what was already created; report it to the user.

```shell
plone-client create-page /docs page.md --publish publish        # Markdown (or --html) to blocks; # heading = title
plone-client create-page /docs - --title "Notes" < notes.md
plone-client create-with-files /news "News Item" lead.jpg more.jpg --title "Title" --publish publish
plone-client create-page /news story.md --type "News Item" --file lead.jpg --publish publish   # page with files and lead image
plone-client upload-tree ./handbook /docs --pages               # folders as pages, .md files as pages
```

`create-page` and `upload-tree --pages` need the `markdown` extra; exit code 3 means it is missing.
`--blocks '{"codeBlock": true}'` chooses the block types the Markdown becomes (code blocks, here), merged over the profile's `blocks` setting; an unknown block type is exit code 2.

## Content model

- Run `plone-client types <type>` before setting fields: the site silently ignores fields a type does not have.
- On Volto sites `Folder` usually cannot be added, and a dry run does not show that.
  For a section such as `/news`, create a `Document`, which is folderish; `plone-client types --addable-in <path>` lists what a folder can hold.
- A News Item's lead image on a Volto site is `preview_image_link`, a relation to an Image inside the item; other sites have an `image` field.
  `create-with-files` picks the right one from the type's schema.
- New items are private until a workflow transition such as `publish` runs; `create` and `create-page` take `--publish`.

## Blocks

The text of a Volto page lives in blocks, not in a text field, and a page without them shows nothing.
To write prose, use `create-page`.
`create` adds a title block and a description block, unless given `--no-blocks` or `blocks` in the data.

`update` with `blocks` replaces all of them.
Before you write or change blocks, read [references/blocks.md](references/blocks.md), or run `plone-client skill show references/blocks.md`.

## Site administration

```shell
plone-client users list -f id,email
plone-client groups add-member Editors jdoe
plone-client registry get plone.site_title
plone-client registry set plone.site_title '"New title"'
plone-client vocabulary plone.app.vocabularies.Keywords
plone-client aliases list /news/item
```

## Anything else

`request` sends any request, for services without a command.

```shell
plone-client request GET /@navroot
plone-client request GET /@search -P portal_type=Image -P b_size=5
plone-client request POST /news/item/@lock -d '{}'
```

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | Unexpected error, or a refused confirmation |
| 2 | Invalid usage, invalid JSON, or a destructive command without `--yes` |
| 3 | Configuration: unknown profile, missing secret, no site configured |
| 4 | Not authenticated, not allowed, the item is locked, or the type cannot be added here |
| 5 | Not found |
| 6 | Invalid request or conflict, such as an id in use or an invalid field |
| 7 | Refused by a read-only profile or `--read-only` |
| 8 | The site could not be reached |
| 9 | Server error |

Run `plone-client <command> --help` for every option of a command.
