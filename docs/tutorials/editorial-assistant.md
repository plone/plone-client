---
myst:
  html_meta:
    "description": "Build an editorial assistant with plone-client: one MCP server for two sites, one read-only, that prepares a news item with images and publishes it after your approval."
    "property=og:description": "Build an editorial assistant with plone-client: one MCP server for two sites, one read-only, that prepares a news item with images and publishes it after your approval."
    "property=og:title": "Build an editorial assistant"
---

(tutorial-editorial-assistant)=

# Build an editorial assistant

In this tutorial, we will set up an {term}`assistant` that helps a team publish news.
It will work on two sites from one {term}`MCP` server: it can write to the blog, and it can only read the documentation.
It will prepare a news item with two images, show us the plan, wait for our approval, apply it, and publish.

At the end you will have a server that you can register with any assistant, and you will have seen every tool call of one editorial task.

You need [uv](https://docs.astral.sh/uv/), [Docker](https://www.docker.com/), [jq](https://jqlang.org/), and Python 3.12 or later.
You do not need an assistant: a small script makes the same calls, so that you can see each answer.

<!-- check: start -->

## Start a Plone site

We will work on a throwaway site with {term}`Volto` and sample content, described in {ref}`howto-run-a-site`.
Get the Compose file, and start the site.

<!-- check: skip -->
```shell
curl -O https://raw.githubusercontent.com/plone/plone-client/main/docker-compose.yml
```

<!-- check: skip -->
```shell
docker compose up --wait
```

Open `http://localhost:3000` to see the site.
The user is `admin`, and the password is `admin`.

## Install plone-client

<!-- check: skip -->
```shell
uv tool install "plone-client[cli,mcp,markdown]"
```

## Describe the two sites

Each site is a {term}`profile`.
This tutorial points both at the same Compose site, so that it needs only one.
On real sites, only the URLs differ.

The assistant picks a site by its description, so say what each one is for.

<!-- check: stdin admin -->
```shell
plone-client profile add blog --url http://localhost:8080/Plone --username admin --frontend-url http://localhost:3000 --description "The team blog: news goes in /news"
```

When asked for the password, type `admin`.
To avoid the prompt, keep the password in an environment variable; see {ref}`howto-profiles`.
The second profile is {term}`read-only`.

<!-- check: stdin admin -->
```shell
plone-client profile add docs --url http://localhost:8080/Plone --username admin --frontend-url http://localhost:3000 --description "Documentation: read it, never change it" --read-only
```

Put them in a {term}`group`, so that adding a site later needs no change in the assistant.

```shell
plone-client profile group-set editorial blog docs
```

## Register the server

Everything an assistant needs is one command.
For the first pass, we add `--dry-run`, so nothing can change.

<!-- check: skip -->
```shell
plone-client mcp --group editorial --dry-run
```

{ref}`howto-assistant` shows where this command goes in each assistant.
This server offers every tool, including `delete_content` and `call_service`, on the blog.
On a real site, offer fewer with `--tool`; {ref}`howto-protect` has sets to start from.

## Stand in for the assistant

This script calls one tool of the server, the way an assistant does.
Save it as `ask.py`.

<!-- check: file ask.py -->
```python
"""Call one tool of the plone-client MCP server, as an assistant does."""

import asyncio
import json
import os
import shlex
import sys

from mcp import Client
from mcp import StdioServerParameters


async def main(server: str, tool: str, arguments: dict) -> int:
    command = StdioServerParameters(
        command="plone-client", args=shlex.split(server), env=dict(os.environ)
    )
    async with Client(command) as client:
        result = await client.call_tool(tool, arguments)
    print(result.content[0].text)
    return 1 if result.is_error else 0


server, tool, *rest = sys.argv[1:]
sys.exit(asyncio.run(main(server, tool, json.loads(rest[0]) if rest else {})))
```

Get two images to work with, from the sample content.
The sample site has one image, so both are the same picture.

```shell
plone-client -p blog download /media/logo.png -o lead.png
cp lead.png stage.png
```

## Give the assistant its task

This is the prompt you would write.

> Create a news item about the conference on the blog, with `lead.png` as its lead image and `stage.png` inside it.
> Prepare it for publication, and show me a preview before you change anything.

The calls below are the ones the server's {term}`instructions` lead a model to.
The script makes them in a fixed order, so that you can follow them; a real model chooses its own.

First, which sites are there?

```shell
python ask.py "mcp --group editorial --dry-run" list_sites
```

```json
{
  "items": [
    {
      "name": "blog",
      "url": "http://localhost:8080/Plone",
      "description": "The team blog: news goes in /news",
      "read_only": false,
      "blocks": {}
    },
    {
      "name": "docs",
      "url": "http://localhost:8080/Plone",
      "description": "Documentation: read it, never change it",
      "read_only": true,
      "blocks": {}
    }
  ]
}
```

Notice that the documentation site says `read_only`.
The model sees the names, URLs, and descriptions, and never a password.

Which types can it add to `/news`?

```shell
python ask.py "mcp --group editorial --dry-run" content_types '{"site": "blog", "addable_in": "/news"}' | jq -c '.items[] | select(.addable)'
```

```text
{"id":"Event","title":"Event","addable":true}
{"id":"File","title":"File","addable":true}
{"id":"Image","title":"Image","addable":true}
{"id":"Link","title":"Link","addable":true}
{"id":"News Item","title":"News Item","addable":true}
{"id":"Document","title":"Page","addable":true}
```

Which blocks does this site have?
The answer comes from Volto, because the profile has a `frontend_url`.

```shell
python ask.py "mcp --group editorial --dry-run" block_types '{"site": "blog"}' | head -n 5
```

```text
# Blocks

The blocks available on this site. Follow a block's link for its documentation and the schema of its settings. Block data is stored in the `blocks` field of a content item, keyed by block ID, with the block type in `@type`, and their order is in `blocks_layout.items`.

- [Title](http://localhost:3000/@blocks-schema/title) (`title`): Shows the title of the content item. It is part of the default layout of new pages, and a page normally has exactly one. _Offered depending on the content._
```

Now the item itself, in the dry run.

```shell
python ask.py "mcp --group editorial --dry-run" create_content_with_files '{"site": "blog", "parent": "/news", "portal_type": "News Item", "files": ["lead.png", "stage.png"], "data": {"title": "Conference announced", "description": "Join us in October."}}' | jq '{dry_run, created, requests: [.requests[] | "\(.method) \(.url)"]}'
```

```json
{
  "dry_run": true,
  "created": [
    {
      "@id": "http://localhost:8080/Plone/news/conference-announced",
      "@type": "News Item",
      "id": "conference-announced",
      "title": "Conference announced",
      "planned": true
    },
    {
      "@id": "http://localhost:8080/Plone/news/conference-announced/lead.png",
      "@type": "Image",
      "id": "lead.png",
      "title": "lead.png",
      "planned": true,
      "source": "lead.png"
    },
    {
      "@id": "http://localhost:8080/Plone/news/conference-announced/stage.png",
      "@type": "Image",
      "id": "stage.png",
      "title": "stage.png",
      "planned": true,
      "source": "stage.png"
    }
  ],
  "requests": [
    "GET http://localhost:8080/Plone/++api++/@types/News%20Item",
    "POST http://localhost:8080/Plone/++api++/news",
    "POST http://localhost:8080/Plone/++api++/news/conference-announced",
    "POST http://localhost:8080/Plone/++api++/news/conference-announced",
    "PATCH http://localhost:8080/Plone/++api++/news/conference-announced"
  ]
}
```

This is the preview that the assistant shows you.
Each entry in `created` has `planned`, and each request in the list is one that a real run would send.
The last request sets the {term}`lead image`, `preview_image_link`, and you did not have to know that.

## Try the site that is read-only

If the model picks the wrong site, the server refuses before it sends anything.

<!-- check: exit 1 -->
```shell
python ask.py "mcp --group editorial" create_content '{"site": "docs", "parent": "/news", "portal_type": "News Item", "data": {"title": "Wrong site"}}'
```

```text
Error executing tool create_content: {"error": {"type": "PloneReadOnlyError", "message": "POST /news refused: the client is read-only"}}
```

## Approve and apply

You read the preview, and you agree.
A {term}`dry run` is a mode of the server, not a step of a conversation, so your approval is to start the server again.
Start it without `--dry-run`, and repeat the call.

```shell
python ask.py "mcp --group editorial" create_content_with_files '{"site": "blog", "parent": "/news", "portal_type": "News Item", "files": ["lead.png", "stage.png"], "data": {"title": "Conference announced", "description": "Join us in October."}}' | jq '{item, created: [.created[].id]}'
```

```json
{
  "item": {
    "@id": "http://localhost:8080/Plone/news/conference-announced",
    "@type": "News Item",
    "UID": "2acdcf90ad814581a3c52f8dca47a6c3",
    "id": "conference-announced",
    "title": "Conference announced",
    "review_state": "private"
  },
  "created": [
    "conference-announced",
    "lead.png",
    "stage.png"
  ]
}
```

The item is private, so only editors can see it.
Open `http://localhost:3000/news/conference-announced` while logged in, and look at it.

Which transitions can it run?

```shell
python ask.py "mcp --group editorial" get_workflow '{"site": "blog", "path": "/news/conference-announced"}' | jq -c '.state, [.transitions[].id]'
```

```text
{"id":"private","title":"Private"}
["publish","submit"]
```

Publish it.

```shell
python ask.py "mcp --group editorial" run_transition '{"site": "blog", "path": "/news/conference-announced", "transition": "publish"}' | jq .review_state
```

```text
"published"
```

Check the result with the command line.

```shell
plone-client -p blog get /news/conference-announced -f review_state,preview_image_link
```

```json
{
  "review_state": "published",
  "preview_image_link": {
    "@id": "http://localhost:8080/Plone/news/conference-announced/lead.png",
    "@type": "Image",
    "UID": "ad9367a1f8154fc7a51ce2152684b5de",
    "description": "",
    "effective": "1969-12-31T00:00:00+00:00",
    "end": null,
    "getObjSize": null,
    "getRemoteUrl": null,
    "head_title": null,
    "image_field": null,
    "image_scales": {
      "image": [
        {
          "content-type": "image/png",
          "download": "@@images/image-64-9978de452d2660c85bf3dea71596ef7b.png",
          "filename": "lead.png",
          "height": 64,
          "scales": {
            "icon": {
              "download": "@@images/image-32-4a31d23b204b92bcfc20fb7498875837.png",
              "height": 32,
              "width": 32
            },
            "tile": {
              "download": "@@images/image-64-9978de452d2660c85bf3dea71596ef7b.png",
              "height": 64,
              "width": 64
            }
          },
          "size": 177,
          "width": 64
        }
      ]
    },
    "mime_type": null,
    "nav_title": null,
    "review_state": null,
    "start": null,
    "title": "lead.png",
    "type_title": "Image"
  }
}
```

<!-- check: stop -->

You have one server for two sites, a preview that you approve before anything changes, a site that the assistant cannot touch, and a published news item with a lead image.

## Clean up

Stop the site, which throws away its content, and remove the profiles and their passwords.

<!-- check: skip -->
```shell
docker compose down -v
plone-client profile remove blog
plone-client profile remove docs
```

## Next steps

- {ref}`howto-assistant` registers this server with your assistant.
- {ref}`howto-protect` narrows what it can do, with a short list of tools.
- {ref}`howto-custom-agent` writes the same flow as your own Python program.
- {ref}`howto-troubleshoot` helps when something goes wrong.
