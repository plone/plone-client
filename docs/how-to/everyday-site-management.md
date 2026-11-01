---
myst:
  html_meta:
    "description": "Recipes for common jobs on a Plone site from the command line: audits, stale content, bulk publishing, moves, users, the registry, and exports."
    "property=og:description": "Recipes for common jobs on a Plone site from the command line: audits, stale content, bulk publishing, moves, users, the registry, and exports."
    "property=og:title": "Everyday site management"
---

(howto-everyday)=

# Everyday site management

This guide collects recipes for jobs that come up on any {term}`Plone` site.
Each one names its goal, the commands, the output on the sample site, and how to verify and adapt it.
The outputs follow from running the recipes in order, so an earlier recipe can change what a later one finds.

## Before you start

You need the command line, [jq](https://jqlang.org/), and a {term}`profile`.
The examples run against the {term}`Compose site`, whose sample content {ref}`howto-run-a-site` describes.

<!-- check: start -->

<!-- check: stdin admin -->
```shell
plone-client profile add local --url http://localhost:8080/Plone --username admin --frontend-url http://localhost:3000 --use
```

If a command fails, look for its error in {ref}`howto-troubleshoot`.

## Audit unpublished content

**Goal:** list what visitors cannot see yet.

**Prerequisites:** a profile with a user who can see private items.

```shell
plone-client search --state private -f @id,title
plone-client search --state pending -f @id,title
```

```text
[
  {
    "@id": "http://localhost:8080/Plone/about/team",
    "title": "Team"
  },
  {
    "@id": "http://localhost:8080/Plone/news/release-party",
    "title": "Release party in Brasília"
  },
  {
    "@id": "http://localhost:8080/Plone/news/release-notes-draft",
    "title": "Release notes draft"
  }
]
[
  {
    "@id": "http://localhost:8080/Plone/news/sprint-report",
    "title": "Sprint report"
  }
]
```

**Verify:** count the same search.

```shell
plone-client search --state private -t "News Item" --count
```

```json
{
  "items_total": 2
}
```

**Adapt:** drop `-t` to include every {term}`content type`, or pass a path, such as `search /news`, to look inside one folder.

## Find stale content

**Goal:** list items that nobody changed after a date.

**Prerequisites:** none.

`--index` passes any catalog query.
Every item of the sample site is older than the date below, so all five news items match.

```shell
plone-client search /news -t "News Item" -i 'modified:={"query": "2100-01-01", "range": "max"}' --sort-on modified -m modified -f @id,modified --limit 2
```

```json
[
  {
    "@id": "http://localhost:8080/Plone/news/release-6-2",
    "modified": "2026-11-01T03:08:30+00:00"
  },
  {
    "@id": "http://localhost:8080/Plone/news/release-party",
    "modified": "2026-11-01T03:08:30+00:00"
  }
]
```

**Verify:** the `modified` date of each result is before the date you gave.

**Adapt:** change the date, or use `"range": "min"` for items changed after it.
Raise `--limit`, which is 50 by default.

## Publish in bulk

**Goal:** publish the private items whose title starts with `Release`.

**Prerequisites:** a user who can publish.

Select the items with `jq`, and preview each {term}`transition` with `-n`.

```shell
plone-client search /news -t "News Item" --state private -c -f @id,title | jq -r '.[] | select(.title | startswith("Release")) | ."@id"' > to-publish.txt
xargs -I{} plone-client -c -n workflow {} publish < to-publish.txt
```

```text
{"dry_run": true, "method": "POST", "url": "http://localhost:8080/Plone/++api++/news/release-party/@workflow/publish"}
{"dry_run": true, "method": "POST", "url": "http://localhost:8080/Plone/++api++/news/release-notes-draft/@workflow/publish"}
```

When the requests look right, run the same line without `-n`.

```shell
xargs -I{} plone-client -c workflow {} publish -f review_state < to-publish.txt
```

```text
{"review_state": "published"}
{"review_state": "published"}
```

**Verify:** nothing private is left.

```shell
plone-client search /news -t "News Item" --state private --count
```

```json
{
  "items_total": 0
}
```

**Adapt:** pass `--comment` to record why in the history, or `--effective` to set the publication date.
These lines look only in `/news`: search from `/` to cover the whole site.
They use the current {term}`profile`: with several sites, add `-p NAME` to each `plone-client` command.
To publish a folder and everything inside it, use `workflow /news publish --recursive`.

## Move a subtree and keep its old address

**Goal:** archive an item without breaking links to it.

**Prerequisites:** a folder to move into.

```shell
plone-client create / Document --id archive --title Archive --publish publish -f @id,review_state
plone-client move /news/old-announcement --to /archive
```

```text
{
  "@id": "http://localhost:8080/Plone/archive",
  "review_state": "published"
}
[
  {
    "source": "http://localhost:8080/Plone/news/old-announcement",
    "target": "http://localhost:8080/Plone/archive/old-announcement"
  }
]
```

Plone redirects the old path by itself.
Add another alias if the item was known under a different address.

```shell
plone-client aliases add /archive/old-announcement /old-news -c
```

```json
{"@id": "http://localhost:8080/Plone/archive/old-announcement/@aliases", "items": [{"path": "/news/old-announcement"}, {"path": "/old-news"}], "items_total": 2}
```

**Verify:** list the aliases of the item in its new place.

```shell
plone-client aliases list /archive/old-announcement -f items
```

```json
{
  "items": [
    {
      "path": "/news/old-announcement"
    },
    {
      "path": "/old-news"
    }
  ]
}
```

**Adapt:** `move` takes several items, and a folder moves with everything inside it.
`copy` takes the same options and leaves the original in place.

## Reorder a folder

**Goal:** put an item first in its folder, which is the order `ls` and menus show.

**Prerequisites:** none.

```shell
plone-client order /news sprint-report top
```

```json
[
  "http://localhost:8080/Plone/news/sprint-report",
  "http://localhost:8080/Plone/news/release-6-2",
  "http://localhost:8080/Plone/news/release-party",
  "http://localhost:8080/Plone/news/release-notes-draft"
]
```

**Verify:** `ls` shows the new order.

```shell
plone-client ls /news -f title -c
```

```json
[{"title": "Sprint report"}, {"title": "Release 6.2 is out"}, {"title": "Release party in Brasília"}, {"title": "Release notes draft"}]
```

**Adapt:** the last argument takes `top`, `bottom`, `up`, `down`, or a number of positions, where `-2` is two up.

## Add users from a CSV file

**Goal:** create accounts from a list, and put them in a group.

**Prerequisites:** a CSV file without a header line.

<!-- check: file people.csv -->
```text
asmith,asmith@example.org,Ana Smith
bjones,bjones@example.org,Bo Jones
```

`--no-send-reset` skips the welcome email, which needs a mail server.
Remove it on a site with one, so that each user gets a link to set a password.

```shell
while IFS=, read -r id email name; do
  plone-client users create "$id" --email "$email" --fullname "$name" --no-send-reset -d '{"password": "correct-horse-battery"}' -f id -c
  plone-client groups add-member editors "$id" -f items -c
done < people.csv
```

```text
{"id": "asmith"}
{"items": ["asmith", "jdoe"]}
{"id": "bjones"}
{"items": ["asmith", "bjones", "jdoe"]}
```

**Verify:** list the members of the group.

```shell
plone-client users list --group editors -f id,fullname
```

```json
[
  {
    "id": "asmith",
    "fullname": "Ana Smith"
  },
  {
    "id": "bjones",
    "fullname": "Bo Jones"
  },
  {
    "id": "jdoe",
    "fullname": "Jo Doe"
  }
]
```

**Adapt:** pass `--role` to `users create` for a global role.
Give a group access to one folder with {ref}`howto-users-sharing`.

## Compare a registry record across sites

**Goal:** read one setting on every site you manage.

**Prerequisites:** a profile per site.

The second profile here is the same site, read-only, to stand in for production.

```shell
plone-client profile add production --url http://localhost:8080/Plone --username admin --secret env --read-only -c
```

```json
{"name": "production", "url": "http://localhost:8080/Plone", "username": "admin", "secret": "env", "read_only": true, "current": false}
```

```shell
export PLONE_CLIENT_PASSWORD=admin
for profile in local production; do
  echo "$profile: $(plone-client -p "$profile" registry get plone.site_title)"
done
```

```text
local: "Welcome to Plone 6"
production: "Welcome to Plone 6"
```

Change it on one site.
The value is JSON, so a text needs its own quotes.

```shell
plone-client registry set plone.site_title '"Sample site"'
```

```json
{
  "plone.site_title": "Sample site"
}
```

**Verify:** a read-only profile refuses the same change, with exit code 7.

<!-- check: exit 7 -->
```shell
plone-client -p production registry set plone.site_title '"Sample site"'
```

```json
{
  "error": {
    "type": "PloneReadOnlyError",
    "message": "PATCH /@registry refused: the client is read-only"
  }
}
```

**Adapt:** `registry list` with a text finds the names of records.

## Call a service without a command

**Goal:** use a `plone.restapi` service or an add-on service that has no command.

**Prerequisites:** the service's path, from its documentation.

```shell
plone-client request GET /@site -f @id,plone.site_title
```

```json
{
  "@id": "http://localhost:8080/Plone/@site",
  "plone.site_title": "Sample site"
}
```

```shell
plone-client request POST /news/release-6-2/@lock -d '{}' -f locked,stealable
plone-client request DELETE /news/release-6-2/@lock -f locked
```

```text
{
  "locked": true,
  "stealable": true
}
{
  "locked": false
}
```

**Verify:** `request GET /news/release-6-2/@lock` shows the state of the lock.

**Adapt:** `-P key=value` adds query parameters, and `-H 'Name: value'` adds headers.
{ref}`howto-call-other-services` does the same from Python.

## Export metadata to CSV

**Goal:** give someone a spreadsheet of the content.

**Prerequisites:** none.

`-m` asks the catalog for extra columns, and `jq` turns each result into a line.

```shell
plone-client search /news -t "News Item" --sort-on sortable_title -c -m review_state -f title,review_state | jq -r '.[] | [.title, .review_state] | @csv' > news.csv
cat news.csv
```

```text
"Release 6.2 is out","published"
"Release notes draft","published"
"Release party in Brasília","published"
"Sprint report","pending"
```

**Verify:** the number of lines matches the count of the search.

```shell
wc -l < news.csv | tr -d ' '
```

```text
4
```

**Adapt:** `-m _all` returns every catalog column.
Raise `--limit` on a site with more than 50 matches.

<!-- check: stop -->

## Related

- {ref}`reference-cli` lists every command and option.
- {ref}`reference-cheat-sheet` lists the commands by task.
- {ref}`howto-scripts-ci` runs these recipes without a terminal.
- {ref}`howto-preview-changes` compares `-n` and `--read-only`.
