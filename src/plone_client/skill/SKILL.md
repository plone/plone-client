---
name: plone-client
description: Read and change content on a Plone site with the plone-client command line — list, search, create, update, publish, upload, and delete items, manage users and groups, and call any plone.restapi service. Use when the user asks to work with a Plone site's content or configuration, or mentions plone-client, plone.restapi, Volto content, or a Plone profile.
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
- Use `-f` to keep only the keys you need, so the output stays small.

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
plone-client blocks /news/item           # summary of the Volto blocks
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
plone-client upload-tree ./handbook /docs --pages               # folders as pages, .md files as pages
```

`create-page` and `upload-tree --pages` need the `markdown` extra; exit code 3 means it is missing.

## Content model

- Run `plone-client types <type>` before setting fields: the site silently ignores fields a type does not have.
- On Volto sites there is usually no `Folder` type; `Document` items are folderish.
- A News Item's lead image on a Volto site is `preview_image_link`, a relation to an Image inside the item; other sites have an `image` field.
  `create-with-files` picks the right one from the type's schema.
- `create` adds a title block and a description block unless given `--no-blocks` or `blocks` in the data.
- Before writing blocks by hand, run `plone-client block-types --markdown` for the blocks the site offers, and `plone-client block-types <block> --markdown` for the data one takes.
  A `"source": "builtin"` answer describes only Volto's core blocks: the site did not say which blocks it has.

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
| 4 | Not authenticated, not allowed, or the item is locked |
| 5 | Not found |
| 6 | Invalid request or conflict |
| 7 | Refused by a read-only profile or `--read-only` |
| 8 | The site could not be reached |
| 9 | Server error |

Run `plone-client <command> --help` for every option of a command.
