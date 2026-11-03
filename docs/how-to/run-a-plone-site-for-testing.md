---
myst:
  html_meta:
    "description": "Start a throwaway Plone site with Volto and sample content with Docker Compose, point a profile at it, and reset it."
    "property=og:description": "Start a throwaway Plone site with Volto and sample content with Docker Compose, point a profile at it, and reset it."
    "property=og:title": "Run a Plone site for testing"
---

(howto-run-a-site)=

# Run a Plone site for testing

This guide shows you how to start a {term}`Compose site`: a throwaway {term}`Plone` site with {term}`Volto` and sample content, on your computer.
The tutorials, the checks of this documentation, and the integration tests all use it.

You need [Docker](https://www.docker.com/) with Compose.

## Start the site

Download the Compose file, and start it.

<!-- check: start -->
<!-- check: skip -->
```shell
curl -O https://raw.githubusercontent.com/plone/plone-client/main/docker-compose.yml
docker compose up --wait
```

`--wait` returns when the site answers, usually in less than a minute.
Open `http://localhost:3000` to see the site, and log in with the user `admin` and the password `admin`.
These credentials belong to the throwaway {term}`Compose site`; never reuse them on a real site.

To work on a copy of this repository, use the file at its root, which is the same one.

## What the file starts

```{literalinclude} ../../docker-compose.yml
:language: yaml
```

| Service | What it is | Address on your computer |
|---|---|---|
| `plone` | The backend, with a site with the id `Plone`. | `http://localhost:8080/Plone` |
| `volto` | The frontend, which talks to the backend inside Docker. | `http://localhost:3000` |
| `seed` | A script that creates the sample content, and exits. | None |
| `mcp` | Only with `--profile mcp`: the MCP server over HTTP. See {ref}`howto-assistant`. | `http://localhost:8000` |

## What the sample content is

The `seed` service runs [`seed.py`](https://github.com/plone/plone-client/blob/main/docs/_checks/seed.py) once, and skips what already exists.

| Content | State |
|---|---|
| `/news`, `/about`, `/media`: pages | Published |
| `/about/team`: a page | Private |
| `/news/release-6-2`, `/news/old-announcement`: news items | Published |
| `/news/release-party`, `/news/release-notes-draft`: news items | Private |
| `/news/sprint-report`: a news item | Pending |
| `/media/logo.png`: an image | No {term}`workflow` |
| `/media/readme.txt`: a file | No workflow |
| `jdoe`: a user with the role `Member`, in the group `editors` | |
| `editors`: a group with the role `Editor` | |

## Point a profile at it

Set `--frontend-url` too, so that `block-types` can ask Volto which blocks the site has.

<!-- check: stdin admin -->
```shell
plone-client profile add local --url http://localhost:8080/Plone --username admin --frontend-url http://localhost:3000 --use
```

When asked for the password, type `admin`.
Check that it works.

```shell
plone-client ls /news -f id,review_state -c
```

```text
[{"review_state": "published"}, {"review_state": "private"}, {"review_state": "private"}, {"review_state": "pending"}, {"review_state": "published"}]
```

<!-- check: stop -->

## Choose other versions or ports

Environment variables change what the file starts.

| Variable | Default | Changes |
|---|---|---|
| `PLONE_IMAGE` | `plone/plone-backend:6.1` | The backend image. |
| `VOLTO_IMAGE` | `plone/plone-frontend:19.6.1` | The frontend image. |
| `PLONE_PORT` | `8080` | The port of the backend on your computer. |
| `VOLTO_PORT` | `3000` | The port of the frontend on your computer. |

For example, this runs Plone 6.2 on other ports, next to a site that uses the default ones.

```shell
PLONE_IMAGE=plone/plone-backend:6.2 PLONE_PORT=8081 VOLTO_PORT=3001 docker compose -p other up --wait
```

## Reset the site

Remove the containers and their data, and start again.

```shell
docker compose down -v
docker compose up --wait
```

This also recovers from a tutorial that failed half way; remove the profiles it created with `plone-client profile remove NAME`.

## How the checks use it

In a copy of this repository, `make docs-check` starts this site for each page, runs the page's commands, compares their output with the page, and removes the site.
`make test-integration` starts the `plone` and `volto` services on free ports.

## Related

- {ref}`tutorial-first-cli-session` uses this site from a terminal.
- {ref}`tutorial-first-script` uses it from Python.
- {ref}`reference-compatibility` lists the images that the tests cover.
