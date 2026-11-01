---
myst:
  html_meta:
    "description": "The plone-client commands by task, on one page: connect, inspect, search, create, update, publish, move, upload, users, protect, and automate."
    "property=og:description": "The plone-client commands by task, on one page: connect, inspect, search, create, update, publish, move, upload, users, protect, and automate."
    "property=og:title": "Cheat sheet"
---

(reference-cheat-sheet)=

# Cheat sheet

The commands of `plone-client` by task.
Each name links to its options in {ref}`reference-cli`.
`<ref>` is a path, a URL inside the site, `uid:<UID>`, or a `resolveuid` link.

## Connect

| Task | Command | Reference |
|---|---|---|
| Add a site | `plone-client profile add prod --url https://example.org --username admin --use` | {ref}`profile add <cli-profile-add>` |
| Add a read-only site | `plone-client profile add prod --url https://example.org --username admin --read-only` | {ref}`profile add <cli-profile-add>` |
| List the sites | `plone-client profile list` | {ref}`profile list <cli-profile-list>` |
| Switch sites | `plone-client profile use staging` | {ref}`profile use <cli-profile-use>` |
| One command on another site | `plone-client -p staging ls /` | {ref}`reference-cli-global-options` |
| See who you are | `plone-client info` | {ref}`info <cli-info>` |

## Inspect

| Task | Command | Reference |
|---|---|---|
| Print an item | `plone-client get /news/item` | {ref}`get <cli-get>` |
| List a folder | `plone-client ls /news -f @id,title,review_state` | {ref}`ls <cli-ls>` |
| Summarize the blocks of an item | `plone-client blocks /news/item` | {ref}`blocks <cli-blocks>` |
| Find an item by UID | `plone-client resolve uid:<UID>` | {ref}`resolve <cli-resolve>` |
| Show the history | `plone-client history /news/item` | {ref}`history <cli-history>` |
| Show who has access | `plone-client sharing /news/item` | {ref}`sharing <cli-sharing>` |
| List the content types | `plone-client types` | {ref}`types <cli-types>` |
| Show the fields of a type | `plone-client types "News Item"` | {ref}`types <cli-types>` |
| List the blocks of the site | `plone-client block-types` | {ref}`block-types <cli-block-types>` |
| List the terms of a vocabulary | `plone-client vocabulary plone.app.vocabularies.Keywords` | {ref}`vocabulary <cli-vocabulary>` |

## Search

| Task | Command | Reference |
|---|---|---|
| Search by text | `plone-client search -q "keyword"` | {ref}`search <cli-search>` |
| Search by type and state | `plone-client search /news -t "News Item" --state private` | {ref}`search <cli-search>` |
| Search any index | `plone-client search -i Subject=plone` | {ref}`search <cli-search>` |
| Count the results | `plone-client search --state pending --count` | {ref}`search <cli-search>` |
| Sort the results | `plone-client search --sort-on modified --reverse` | {ref}`search <cli-search>` |

## Create and update

| Task | Command | Reference |
|---|---|---|
| Create an item | `plone-client create /news "News Item" --title "Title"` | {ref}`create <cli-create>` |
| Create a page from Markdown | `plone-client create-page /docs page.md` | {ref}`create-page <cli-create-page>` |
| Create an item with files | `plone-client create-with-files /news "News Item" lead.jpg --title "Title"` | {ref}`create-with-files <cli-create-with-files>` |
| Change fields | `plone-client update /news/item --title "New title"` | {ref}`update <cli-update>` |
| Set a list field | `plone-client update /news/item -s subjects:='["plone"]'` | {ref}`update <cli-update>` |
| Delete an item | `plone-client delete /news/old` | {ref}`delete <cli-delete>` |

## Publish

| Task | Command | Reference |
|---|---|---|
| Show the state and transitions | `plone-client workflow /news/item` | {ref}`workflow <cli-workflow>` |
| Publish an item | `plone-client workflow /news/item publish` | {ref}`workflow <cli-workflow>` |
| Publish a folder and its contents | `plone-client workflow /news publish --recursive` | {ref}`workflow <cli-workflow>` |
| Create and publish at once | `plone-client create /news "News Item" --title "Title" --publish publish` | {ref}`create <cli-create>` |

## Move

| Task | Command | Reference |
|---|---|---|
| Move an item | `plone-client move /news/old --to /archive` | {ref}`move <cli-move>` |
| Copy an item | `plone-client copy /news/item --to /archive` | {ref}`copy <cli-copy>` |
| Put an item first in its folder | `plone-client order /news item top` | {ref}`order <cli-order>` |
| Redirect an old path | `plone-client aliases add /news/item /old-path` | {ref}`aliases add <cli-aliases-add>` |

## Upload and download

| Task | Command | Reference |
|---|---|---|
| Upload files | `plone-client upload /media photo.jpg report.pdf` | {ref}`upload <cli-upload>` |
| Upload a large file in chunks | `plone-client upload /media video.mp4 --tus` | {ref}`upload <cli-upload>` |
| Upload a folder as pages | `plone-client upload-tree ./handbook /docs --pages` | {ref}`upload-tree <cli-upload-tree>` |
| Download a file | `plone-client download /media/report.pdf -o report.pdf` | {ref}`download <cli-download>` |

## Users and settings

| Task | Command | Reference |
|---|---|---|
| List users | `plone-client users list -f id,email` | {ref}`users list <cli-users-list>` |
| Create a user | `plone-client users create jdoe --email jdoe@example.org` | {ref}`users create <cli-users-create>` |
| Add a user to a group | `plone-client groups add-member editors jdoe` | {ref}`groups add-member <cli-groups-add-member>` |
| Read a setting | `plone-client registry get plone.site_title` | {ref}`registry get <cli-registry-get>` |
| Change a setting | `plone-client registry set plone.site_title '"New title"'` | {ref}`registry set <cli-registry-set>` |

## Protect a site

| Task | Command | Reference |
|---|---|---|
| Preview a change | `plone-client -n delete /news/old` | {ref}`howto-preview-changes` |
| Refuse every change | `plone-client --read-only update /news/item --title "Title"` | {ref}`howto-preview-changes` |
| Confirm in advance | `plone-client delete /news/old --yes` | {ref}`reference-cli-confirmation` |

## Automate

| Task | Command | Reference |
|---|---|---|
| Keep only some keys | `plone-client ls /news -f @id,title` | {ref}`reference-cli-output` |
| Print JSON on one line | `plone-client ls /news -c` | {ref}`reference-cli-output` |
| Log each request | `plone-client -v get /` | {ref}`reference-cli-global-options` |
| Send any request | `plone-client request GET /@navroot` | {ref}`request <cli-request>` |
| Serve a site to an assistant | `plone-client mcp` | {ref}`mcp <cli-mcp>` |
| Give the skill to a coding agent | `plone-client skill install` | {ref}`skill install <cli-skill-install>` |

## Related

- {ref}`howto-everyday` has complete recipes.
- {ref}`howto-scripts-ci` runs commands without a terminal.
