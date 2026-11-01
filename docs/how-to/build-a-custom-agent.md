---
myst:
  html_meta:
    "description": "Write a Python program with plone-client that asks a model for a page, validates its blocks, shows the planned requests, and applies them after human approval."
    "property=og:description": "Write a Python program with plone-client that asks a model for a page, validates its blocks, shows the planned requests, and applies them after human approval."
    "property=og:title": "Build a custom agent"
---

(howto-custom-agent)=

# Build a custom agent

This guide shows you how to write a Python program that asks a language model for the content of a page, and applies it to a Plone site only after a person approves.
The library does the Plone work, your code decides what the model may do, and nothing reaches the site without a yes.

You need a {term}`profile`, or the URL of a site.
The examples use a local site, which {ref}`howto-run-a-site` starts.

<!-- check: start -->

## Isolate the model call

Keep the call to the model in one function that returns plain data, so that you can test the rest without a model.
This stand-in lets you run the program without a key.
Save it as `model.py`.

<!-- check: file model.py -->
```python
def write_page(topic: str) -> dict:
    """A page about a topic, as the model would write it."""
    return {
        "title": f"About {topic}",
        "description": f"A short page about {topic}.",
        "paragraphs": [f"This page is about {topic}.", "It has two paragraphs."],
    }
```

When the program works, replace it with a real call.
This one uses the [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python), which reads its key from `ANTHROPIC_API_KEY`.
Any other model works the same way, as long as the function returns the same shape.

<!-- check: skip -->
```python
import anthropic
import json

PROMPT = """Write a short web page about {topic}.
Answer only with JSON, with the keys title, description, and paragraphs,
which is a list of strings."""


def write_page(topic: str) -> dict:
    """A page about a topic, written by the model."""
    client = anthropic.Anthropic()
    answer = client.messages.create(
        model="claude-opus-5-5",
        max_tokens=1000,
        messages=[{"role": "user", "content": PROMPT.format(topic=topic)}],
    )
    return json.loads(answer.content[0].text)
```

## Write the agent

Save this as `agent.py`.
It builds the blocks in code, so the model cannot produce a page that the site rejects.
It runs the change on a {term}`dry run` client first, prints the plan, and waits.

<!-- check: file agent.py -->
```python
import sys

from model import write_page
from plone_client import blocks
from plone_client import PloneClient

URL = "http://localhost:8080/Plone"
LOGIN = {"username": "admin", "password": "admin"}


def page_data(page: dict) -> dict:
    """Field values for a page, with blocks built and checked."""
    items = [blocks.title(), blocks.description()]
    items += [blocks.text(paragraph) for paragraph in page["paragraphs"]]
    data = {"title": page["title"], "description": page["description"]}
    return blocks.prepare({**data, "blocks": items})


def create(data: dict, dry_run: bool) -> dict:
    """Create the page, or only plan it."""
    with PloneClient(URL, dry_run=dry_run, **LOGIN) as site:
        answer = site.content.create("/news", "Document", data)
        return site.dry_run_log[-1] if dry_run else answer


data = page_data(write_page(sys.argv[1]))
plan = create(data, dry_run=True)
print(plan["method"], plan["url"])
print("title:", plan["json"]["title"])
print("blocks:", len(plan["json"]["blocks"]))
if input("Apply? [y/N] ").strip().lower() != "y":
    sys.exit("Nothing was changed.")
item = create(data, dry_run=False)
print("created", item["@id"], item["review_state"])
```

## Run it

Answer the question with anything but `y`, and nothing changes.

<!-- check: exit 1 -->
<!-- check: stdin n -->
```shell
python agent.py sprints
```

```text
POST http://localhost:8080/Plone/++api++/news
title: About sprints
blocks: 4
Apply? [y/N] Nothing was changed.
```

Answer `y`, and the program sends the same request.

<!-- check: stdin y -->
```shell
python agent.py sprints
```

```text
POST http://localhost:8080/Plone/++api++/news
title: About sprints
blocks: 4
Apply? [y/N] created http://localhost:8080/Plone/news/about-sprints private
```

<!-- check: stop -->

The new page is private, so publishing stays a separate decision.
To publish, call `site.workflow.transition(item["@id"], "publish")` after a second approval.

## Keep the model on a short leash

- Give the model no tools, as here, and let your code call the library.
  What it can do is then what your code does.
- Set `read_only=True` on the client of any site that the program should only read.
- Treat the answer as untrusted: build blocks with {mod}`plone_client.blocks`, and do not pass fields you did not expect.
  A site silently ignores unknown fields.
- Log `site.dry_run_log` with each approval, to know later what was approved.

{ref}`howto-protect` covers the rest.

## Use the MCP server instead when

- The model should choose its own steps, and not follow a fixed program.
- The client already speaks {term}`MCP`, such as an {term}`assistant`.
- You would otherwise rewrite the {term}`tools <tool>` that the server has.

Your program can be the client: {ref}`howto-assistant-python` connects to the server from Python.

## Related

- {ref}`reference-blocks` lists the block helpers.
- {ref}`howto-preview-changes` covers dry runs.
- {ref}`howto-handle-errors` reacts to what a site answers.
