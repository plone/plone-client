---
myst:
  html_meta:
    "description": "Write your first Python script with plone-client: read a public site, create and publish a page, preview a change, and keep news items in sync with a JSON file."
    "property=og:description": "Write your first Python script with plone-client: read a public site, create and publish a page, preview a change, and keep news items in sync with a JSON file."
    "property=og:title": "Your first script"
---

(tutorial-first-script)=

# Your first script

In this tutorial, we will write Python scripts that read a public {term}`Plone` site, create and publish a page on a site of our own, preview a change, and keep three news items in sync with a JSON file.
At the end, you will have a sync script you can run as often as you like: it changes only what differs.
Along the way, you will meet the client, its {term}`managers <manager>`, and the way plone-client answers with plain JSON.

You need [uv](https://docs.astral.sh/uv/) and, from the third section on, [Docker](https://www.docker.com/).

<!-- check: start -->

## Create a project

Create a project and add plone-client to it.
The `cli` extra adds the command line and the {term}`keyring`, which we will use later for a {term}`profile`.

<!-- check: skip -->
```shell
uv init --bare first-script
cd first-script
uv add "plone-client[cli]"
```

## Look at a site before you own one

`https://demo.plone.org` is a public {term}`demo site`, so you can read it without an account.
It is shared with other visitors and resets every night, so we will only read from it, and you may see different content.

Create a file named `demo.py` with this content.

<!-- check: file demo.py -->
```python
from plone_client import PloneClient

client = PloneClient("https://demo.plone.org")
for item in client.search.iter(portal_type="Document", limit=3):
    print(item["review_state"], item["title"])
```

Run it.

<!-- check: demo -->
```shell
uv run python demo.py
```

```text
published Blocks
published Accordion
published Button
```

`client.search` is a {term}`manager`, one of many attributes of the client.
Each manager groups the {term}`plone.restapi` services for one subject, and each method returns the site's JSON answer as Python dictionaries and lists.
`search.iter` goes through every page of results for you, however many there are.

## Start a Plone site

To change content, we need a site of our own.
Get the Compose file, and start the site.

<!-- check: skip -->
```shell
curl -O https://raw.githubusercontent.com/plone/plone-client/main/docker-compose.yml
docker compose up --wait
```

Open `http://localhost:3000` to see it in {term}`Volto`, its web interface, with the user `admin` and the password `admin`.
These credentials belong to the throwaway {term}`Compose site`; never reuse them on a real site.
The site has sample content; {ref}`howto-run-a-site` lists it.
The API of the same site is at `http://localhost:8080/Plone`.

## Connect to the site

Create a file named `script.py` with this content.

<!-- check: file script.py -->
```python
from plone_client import blocks
from plone_client import PloneClient

client = PloneClient("http://localhost:8080/Plone", username="admin", password="admin")
site = client.content.get("/")
print("Connected to", site["title"])
```

Run it.

```shell
uv run python script.py
```

```text
Connected to Plone Site
```

## Create a page

A page on a Volto site is a {term}`content item` of the {term}`content type` `Document`, and its content is a list of {term}`blocks <block>`.
Add these lines to the end of `script.py`.

<!-- check: append script.py -->
```python
if client.content.exists("/hello"):
    page = client.content.get("/hello")
    print("Already there:", page["@id"])
else:
    page = client.content.create(
        "/",
        "Document",
        id="hello",
        title="Hello, Plone",
        description="My first page created with plone-client",
        **blocks.build(blocks.title(), blocks.description(), blocks.text("It works.")),
    )
    print("Created", page["@id"], "in state", page["review_state"])
```

Run the script.

```shell
uv run python script.py
```

```text
Connected to Plone Site
Created http://localhost:8080/Plone/hello in state private
```

Open `http://localhost:3000/hello` to see the page.
{mod}`plone_client.blocks` built the title, description, and text blocks a Volto page needs.
This is what `blocks.build` gives the site: the blocks by ID in `blocks`, and their order in `blocks_layout`.

```shell
uv run python -c 'import json; from plone_client import blocks; print(json.dumps(blocks.build(blocks.title(), blocks.description(), blocks.text("It works.")), indent=2))'
```

```json
{
  "blocks": {
    "8b2ddd1f-07ed-4661-a7df-9cff54a1ef79": {
      "@type": "title"
    },
    "39b45a07-369b-406c-acf6-c45ff9ee84ce": {
      "@type": "description"
    },
    "512db700-c358-4f89-aa99-78411817ece1": {
      "@type": "slate",
      "plaintext": "It works.",
      "value": [
        {
          "type": "p",
          "children": [
            {
              "text": "It works."
            }
          ]
        }
      ]
    }
  },
  "blocks_layout": {
    "items": [
      "8b2ddd1f-07ed-4661-a7df-9cff54a1ef79",
      "39b45a07-369b-406c-acf6-c45ff9ee84ce",
      "512db700-c358-4f89-aa99-78411817ece1"
    ]
  }
}
```

Run the script a second time.

```shell
uv run python script.py
```

```text
Connected to Plone Site
Already there: http://localhost:8080/Plone/hello
```

Notice that nothing was created this time: the script checks first.

## Publish it

New pages are private, which is their {term}`review_state`.
Publishing is a workflow {term}`transition`.
Add these lines to the end of the script.

<!-- check: append script.py -->
```python
if page["review_state"] != "published":
    client.workflow.transition(page["@id"], "publish")
    print("Published", page["@id"])
```

Run the script.

```shell
uv run python script.py
```

```text
Connected to Plone Site
Already there: http://localhost:8080/Plone/hello
Published http://localhost:8080/Plone/hello
```

## Find it again

Add a search at the end of the script.

<!-- check: append script.py -->
```python
for item in client.search.iter(portal_type="Document", review_state="published"):
    print("Found", item["title"])
```

Run the script once more.

```shell
uv run python script.py
```

```text
Connected to Plone Site
Already there: http://localhost:8080/Plone/hello
Found News
Found About
Found Media
Found Hello, Plone
```

The sample pages are there too, and the page is published already, so the script did not publish it again.

## Preview a change

Before changing a site you care about, you can see what a script would send.
A client created with `dry_run=True` reads as usual, and records each change without sending it.
Create a file named `preview.py`.

<!-- check: file preview.py -->
```python
from plone_client import PloneClient

import json


client = PloneClient(
    "http://localhost:8080/Plone", username="admin", password="admin", dry_run=True
)
client.content.update("/hello", title="Hello again")
print(json.dumps(client.dry_run_log, indent=2))
print("The title is still:", client.content.get("/hello")["title"])
```

Run it.

```shell
uv run python preview.py
```

```text
[
  {
    "dry_run": true,
    "method": "PATCH",
    "url": "http://localhost:8080/Plone/++api++/hello",
    "json": {
      "title": "Hello again"
    }
  }
]
The title is still: Hello, Plone
```

Notice that the URL has `++api++` in it: {term}`++api++` is how a request reaches `plone.restapi`, and plone-client adds it for you.

## Keep the password out of your script

A {term}`profile` gives a site a name, and keeps its password in your operating system's {term}`keyring`.
Add one.

<!-- check: stdin admin -->
```shell
uv run plone-client profile add tutorial --url http://localhost:8080/Plone --username admin --frontend-url http://localhost:3000 --use
```

When asked for the password, type `admin`.
From now on, `PloneClient.from_profile("tutorial")` replaces the URL and the password.

## Sync three news items from a file

Now for a real job.
Create a file named `news.json` with three records.

<!-- check: file news.json -->
```json
[
  {"id": "new-office", "title": "Our new office", "description": "We moved."},
  {"id": "summer-sprint", "title": "Summer sprint", "description": "Join us in July."},
  {"id": "annual-report", "title": "Annual report", "description": "The year in numbers."}
]
```

Create a file named `sync.py`.
For each record, it creates a news item if there is none, and changes it if the title or the description differ.
It changes the site only when you pass `--apply`.

<!-- check: file sync.py -->
```python
from pathlib import Path
from plone_client import blocks
from plone_client import PloneClient

import json
import sys


records = json.loads(Path("news.json").read_text())
apply = "--apply" in sys.argv

with PloneClient.from_profile("tutorial", dry_run=not apply) as client:
    known = {
        entry["@id"].rsplit("/", 1)[-1]: entry
        for entry in client.content.children("/news", portal_type="News Item")
    }
    for record in records:
        fields = {"title": record["title"], "description": record["description"]}
        path = f"/news/{record['id']}"
        entry = known.get(record["id"])
        if entry is None:
            page = blocks.build(blocks.title(), blocks.description())
            client.content.create(
                "/news", "News Item", id=record["id"], **fields, **page
            )
            client.workflow.transition(path, "publish")
            print("created", path)
        elif any(entry[name] != value for name, value in fields.items()):
            client.content.update(path, fields, representation=False)
            print("updated", path)
        else:
            print("same", path)
    if not apply:
        print(len(client.dry_run_log), "changes not sent")
```

Run it without `--apply`.

```shell
uv run python sync.py
```

```text
created /news/new-office
created /news/summer-sprint
created /news/annual-report
6 changes not sent
```

Each item takes two requests: one to create it, and one to publish it.
Look at it, and apply it.

```shell
uv run python sync.py --apply
```

```text
created /news/new-office
created /news/summer-sprint
created /news/annual-report
```

Run it again.

```shell
uv run python sync.py --apply
```

```text
same /news/new-office
same /news/summer-sprint
same /news/annual-report
```

Notice that the second run changed nothing.
Now change a record, as an external source would.

```shell
sed -i.bak 's/Summer sprint/Winter sprint/' news.json
uv run python sync.py --apply
```

```text
same /news/new-office
updated /news/summer-sprint
same /news/annual-report
```

Check the result as a visitor would see it, without logging in.

<!-- check: file check.py -->
```python
from plone_client import PloneClient

client = PloneClient("http://localhost:8080/Plone")
for item in client.search.iter("/news", portal_type="News Item", sort_on="sortable_title"):
    print(item["review_state"], item["title"])
```

```shell
uv run python check.py
```

```text
published Annual report
published Old announcement
published Our new office
published Release 6.2 is out
published Winter sprint
```

The private sample items are not in the list, because visitors cannot see them.

You have read a public site, created and published a page, previewed a change, and kept news items in sync with a file, with a script that you can run again at any time.

## Clean up

Stop the site and throw its content away.

<!-- check: skip -->
```shell
docker compose down -v
```

If a step failed, `docker compose down -v` still resets the site, and `plone-client profile remove tutorial` removes the profile you added; then start again from the top.

<!-- check: stop -->

## Next steps

- {ref}`start-script` shows what to read next.
- {ref}`howto-sync` adds deletions and error handling to this sync.
- {ref}`tutorial-migrate` copies content and its images from one place to another.
- {ref}`tutorial-first-cli-session` does the same kind of work from the command line.
- {ref}`howto-troubleshoot` helps when something does not work.
