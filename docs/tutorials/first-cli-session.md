---
myst:
  html_meta:
    "description": "Manage a Plone site from the terminal with plone-client: add a profile, list content, create and publish a page, and preview a change."
    "property=og:description": "Manage a Plone site from the terminal with plone-client: add a profile, list content, create and publish a page, and preview a change."
    "property=og:title": "Your first command line session"
---

(tutorial-first-cli-session)=

# Your first command line session

In this tutorial, we will manage a Plone site from the terminal.
We will add a profile for the site, look at its content, create and publish a page, and preview a change before making it.

You need [uv](https://docs.astral.sh/uv/) and [Docker](https://www.docker.com/).

## Start a Plone site

We will work against a throwaway Plone site running in Docker.
Start it in its own terminal and leave it running.

```shell
docker run --rm -p 8080:8080 -e SITE=Plone -e TYPE=volto plone/plone-backend:6.1
```

Wait until the output shows `Serving on http://0.0.0.0:8080`.
The site is now at `http://localhost:8080/Plone`, with the user `admin` and the password `admin`.

## Install the command line

In another terminal, install plone-client as a tool.

```shell
uv tool install "plone-client[cli]"
```

## Add a profile

A profile gives the site a name, and keeps its password in your operating system's keyring.

```shell
plone-client profile add tutorial --url http://localhost:8080/Plone --username admin --use
```

When asked for the password, type `admin`.
`--use` makes `tutorial` the current profile, so the next commands use it without being told.

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
  "read_only": false,
  "plone_version": "6.1.5"
}
```

Every command prints JSON like this.

## Look at the content

List what is at the root of the site.

```shell
plone-client ls / -f @id,title,review_state
```

`-f` keeps only the keys you name, which keeps the output short.
A new site has little content, so the list may be empty.

## Create a page

```shell
plone-client create / Document --id hello --title "Hello, Plone" --description "Created from the terminal"
```

```json
{
  "@id": "http://localhost:8080/Plone/hello",
  "@type": "Document",
  "UID": "8a1c5a9d0bde4c6b9c3f1e2a7d6b5c4e",
  "id": "hello",
  "title": "Hello, Plone",
  "review_state": "private"
}
```

Your UID will differ.
Notice that the page is private.

## Publish it

Ask which transitions the page has.

```shell
plone-client workflow /hello -f state,transitions
```

Then run one.

```shell
plone-client workflow /hello publish
```

Run `plone-client ls / -f @id,title,review_state` again, and you will see the page published.

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
Run `plone-client get /hello -f title` to see that the page is still there.

## Clean up

Delete the page for real, and remove the profile and its password.

```shell
plone-client delete /hello --yes
plone-client profile remove tutorial
```

You have added a profile, read and changed a site, and previewed a change before making it.
Stop the Plone site with {kbd}`Control-C` in its terminal when you are done.

## Next steps

- {ref}`tutorial-first-script` does the same from Python.
- {ref}`howto-profiles` keeps secrets in a password manager instead.
- {ref}`howto-agents` lets a coding agent use the command line.
