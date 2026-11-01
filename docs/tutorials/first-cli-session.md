---
myst:
  html_meta:
    "description": "Manage a Plone site from the terminal with plone-client: explore a public site, add a profile, publish in bulk, and react to exit codes."
    "property=og:description": "Manage a Plone site from the terminal with plone-client: explore a public site, add a profile, publish in bulk, and react to exit codes."
    "property=og:title": "Your first command line session"
---

(tutorial-first-cli-session)=

# Your first command line session

In this tutorial, we will manage a {term}`Plone` site from the terminal.
We will look around a public demo site, start a site of our own, create and publish a page, and publish a batch of news items after previewing the change.
At the end, you will have a {term}`profile` for your site, and a script that reacts to what the command line reports.

You need [uv](https://docs.astral.sh/uv/) and, for the second half, [Docker](https://www.docker.com/) and [jq](https://jqlang.org/).

<!-- check: start -->

## Install the command line

Install plone-client as a tool.

<!-- check: skip -->
```shell
uv tool install "plone-client[cli]"
```

## Look at a site before you own one

The {term}`demo site` is a public Plone site at `https://demo.plone.org`.
It is shared with other visitors and resets every night, so what you see may differ from what is shown here.

A profile gives a site a name.
Add one for the demo site, and make it read-only so that nothing we type can change the site.

<!-- demo-site: provisional -->
<!-- check: demo -->
```shell
plone-client profile add demo --url https://demo.plone.org --read-only --frontend-url https://demo.plone.org --secret none
```

`--secret none` says that this profile has no password, because we are reading as an anonymous visitor.

Ask who you are on that site.

<!-- demo-site: provisional -->
<!-- check: demo -->
```shell
plone-client -p demo info
```

```json
{
  "profile": "demo",
  "url": "https://demo.plone.org",
  "authenticated": false,
  "username": null,
  "credentials_rejected": false,
  "read_only": true,
  "plone_version": "6.2.2"
}
```

Every command prints JSON like this.
`-p demo` picks the profile for one command.

List what is at the {term}`site root`.
`-f` keeps only the keys you name, which keeps the output short.

<!-- demo-site: provisional -->
<!-- check: demo -->
```shell
plone-client -p demo ls / -f @id,title,review_state
```

```json
[
  {
    "@id": "https://demo.plone.org/plone-foundation.png",
    "title": "Plone Foundation Logo",
    "review_state": null
  },
  {
    "@id": "https://demo.plone.org/images",
    "title": "Images",
    "review_state": "published"
  },
  {
    "@id": "https://demo.plone.org/block",
    "title": "Blocks",
    "review_state": "published"
  },
  {
    "@id": "https://demo.plone.org/content-types",
    "title": "Content Types",
    "review_state": "published"
  },
  {
    "@id": "https://demo.plone.org/vertical-spacing",
    "title": "Vertical Spacing",
    "review_state": "published"
  }
]
```

Notice `review_state`: it is the {term}`workflow` state of each {term}`content item`.

Search the whole site for three pages.

<!-- demo-site: provisional -->
<!-- check: demo -->
```shell
plone-client -p demo search -t Document --limit 3 -f @id,title
```

```json
[
  {
    "@id": "https://demo.plone.org/block",
    "title": "Blocks"
  },
  {
    "@id": "https://demo.plone.org/block/block-accordion",
    "title": "Accordion"
  },
  {
    "@id": "https://demo.plone.org/block/button-block",
    "title": "Button"
  }
]
```

Now try to change something.

<!-- demo-site: provisional -->
<!-- check: demo -->
<!-- check: exit 7 -->
```shell
plone-client -p demo create / Document --title "Not today"
```

```json
{
  "error": {
    "type": "PloneReadOnlyError",
    "message": "POST / refused: the client is read-only"
  }
}
```

The command line refused before sending anything, and exited with code 7.
To write, we need a site of our own.

## Start a Plone site

We will use a throwaway site that runs in Docker, with sample content already in it.
Get the Compose file and start the site.

<!-- check: skip -->
```shell
curl -O https://raw.githubusercontent.com/plone/plone-client/main/docker-compose.yml
```

<!-- check: skip -->
```shell
docker compose up --wait
```

Open `http://localhost:3000` to see the site in your browser.
{ref}`howto-run-a-site` explains what this file starts.

## Add a profile

This profile keeps its password in your operating system's {term}`keyring`.

<!-- check: stdin admin -->
```shell
plone-client profile add tutorial --url http://localhost:8080/Plone --username admin --frontend-url http://localhost:3000 --use
```

When asked for the password, type `admin`.
`--use` makes `tutorial` the current profile, so the next commands use it without being told.
`--frontend-url` names the {term}`Volto` server, which knows the blocks of the site.

Check that it works.

```shell
plone-client info
```

```json
{
  "profile": "tutorial",
  "url": "http://localhost:8080/Plone",
  "authenticated": true,
  "username": "admin",
  "credentials_rejected": false,
  "read_only": false,
  "plone_version": "6.1.5"
}
```

## Look at the content

List the news of the sample site.

```shell
plone-client ls /news -f @id,title,review_state
```

```json
[
  {
    "@id": "http://localhost:8080/Plone/news/release-6-2",
    "title": "Release 6.2 is out",
    "review_state": "published"
  },
  {
    "@id": "http://localhost:8080/Plone/news/release-party",
    "title": "Release party in Brasília",
    "review_state": "private"
  },
  {
    "@id": "http://localhost:8080/Plone/news/release-notes-draft",
    "title": "Release notes draft",
    "review_state": "private"
  },
  {
    "@id": "http://localhost:8080/Plone/news/sprint-report",
    "title": "Sprint report",
    "review_state": "pending"
  },
  {
    "@id": "http://localhost:8080/Plone/news/old-announcement",
    "title": "Old announcement",
    "review_state": "published"
  }
]
```

Two news items are private, one waits for review, and two are published.

Search does the same across the whole site.
`-t` names a {term}`content type`, and `--state` a workflow state.

```shell
plone-client search -t "News Item" --state pending -f @id,title
```

```json
[
  {
    "@id": "http://localhost:8080/Plone/news/sprint-report",
    "title": "Sprint report"
  }
]
```

## Create a page

```shell
plone-client create / Document --id hello --title "Hello, Plone" --description "Created from the terminal"
```

```json
{
  "@id": "http://localhost:8080/Plone/hello",
  "@type": "Document",
  "UID": "9b1ae9466ba44daf9691b0b933f5b7c8",
  "id": "hello",
  "title": "Hello, Plone",
  "review_state": "private"
}
```

Your {term}`UID` will differ.
Notice that the page is private.

## Publish it

Ask which {term}`transitions <transition>` the page has.

```shell
plone-client workflow /hello -f state,transitions
```

```json
{
  "state": {
    "id": "private",
    "title": "Private"
  },
  "transitions": [
    "publish",
    "submit"
  ]
}
```

Then run one.

```shell
plone-client workflow /hello publish -f review_state
```

```json
{
  "review_state": "published"
}
```

## Preview a change

Before changing a site you care about, look at what a command would send.
Add `-n` to delete the page without deleting it.

```shell
plone-client -n delete /hello
```

```json
{
  "deleted": [
    "/hello"
  ],
  "dry_run": true
}
```

Nothing was sent.
The page is still there.

```shell
plone-client get /hello -f title,review_state
```

```json
{
  "title": "Hello, Plone",
  "review_state": "published"
}
```

## Publish a batch of news

Now the real job: publish every private news item at once, and look before we leap.

Find them, and keep their addresses in a file.
`-c` prints JSON on one line, and `jq` takes the `@id` of each result.

```shell
plone-client search /news -t "News Item" --state private -c -f @id | jq -r '.[]."@id"' > drafts.txt
cat drafts.txt
```

```text
http://localhost:8080/Plone/news/release-party
http://localhost:8080/Plone/news/release-notes-draft
```

Run the transition on each one with `-n` first.

```shell
xargs -I{} plone-client -c -n workflow {} publish < drafts.txt
```

```text
{"dry_run": true, "method": "POST", "url": "http://localhost:8080/Plone/++api++/news/release-party/@workflow/publish"}
{"dry_run": true, "method": "POST", "url": "http://localhost:8080/Plone/++api++/news/release-notes-draft/@workflow/publish"}
```

These are the two requests that would go out, and they look right.
Run the same line without `-n`.

```shell
xargs -I{} plone-client -c workflow {} publish -f review_state < drafts.txt
```

```text
{"review_state": "published"}
{"review_state": "published"}
```

Count what is left.

```shell
plone-client search /news -t "News Item" --state private --count
```

```json
{
  "items_total": 0
}
```

## React to what happened

Each kind of failure has its own {term}`exit code`, so a script can tell them apart.
Ask for something that does not exist.

```shell
plone-client get /news/missing -f title
case $? in
  0) echo "Found it." ;;
  5) echo "No such item, so we create it." ;;
  *) echo "Something else went wrong." ;;
esac
```

```text
{
  "error": {
    "status_code": 404,
    "type": "NotFound",
    "message": "Resource not found: http://localhost:8080/Plone/++api++/news/missing",
    "method": "GET",
    "url": "http://localhost:8080/Plone/++api++/news/missing"
  }
}
No such item, so we create it.
```

Errors are JSON on standard error, and the code 5 means not found.
{ref}`reference-cli` lists every code.

## Clean up

Delete the page, remove the profiles, and throw the site away.

```shell
plone-client delete /hello --yes
plone-client profile remove tutorial
```

```json
{
  "deleted": [
    "/hello"
  ],
  "dry_run": false
}
{
  "removed": "tutorial",
  "secret_removed": true
}
```

<!-- check: skip -->
```shell
plone-client profile remove demo
docker compose down -v
```

You have explored a site without an account, added a profile, published a batch of items after previewing the change, and written a script that reacts to exit codes.

<!-- check: stop -->

## Next steps

- {ref}`howto-everyday` has recipes for the jobs you will do next.
- {ref}`howto-profiles` keeps secrets in a password manager.
- {ref}`howto-scripts-ci` runs the command line without a terminal.
- {ref}`tutorial-first-script` does the same from Python.
- {ref}`howto-troubleshoot` helps when a command fails.
