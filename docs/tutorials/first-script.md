---
myst:
  html_meta:
    "description": "Write your first Python script with plone-client: connect to a Plone site, create a page, publish it, and find it again."
    "property=og:description": "Write your first Python script with plone-client: connect to a Plone site, create a page, publish it, and find it again."
    "property=og:title": "Your first script"
---

(tutorial-first-script)=

# Your first script

In this tutorial, we will write a Python script that connects to a Plone site, creates a page, publishes it, and finds it again with a search.
Along the way, you will meet the client, its managers, and the way plone-client answers with plain JSON.

You need [uv](https://docs.astral.sh/uv/) and [Docker](https://www.docker.com/).

## Start a Plone site

We will work against a throwaway Plone site running in Docker.
Start it in its own terminal and leave it running.

```shell
docker run --rm -p 8080:8080 -e SITE=Plone -e TYPE=volto plone/plone-backend:6.1
```

Wait until the output shows `Serving on http://0.0.0.0:8080`.
The site is now at `http://localhost:8080/Plone`, with the user `admin` and the password `admin`.

## Create a project

In another terminal, create a project and add plone-client to it.

```shell
uv init --bare first-script
cd first-script
uv add plone-client
```

## Connect to the site

Create a file named `script.py` with this content.

```python
from plone_client import PloneClient

client = PloneClient("http://localhost:8080/Plone", username="admin", password="admin")
site = client.content.get("/")
print("Connected to", site["title"])
```

Run it.

```shell
uv run python script.py
```

You should see the title of the site.

```text
Connected to Plone Site
```

`client.content` is a manager, one of many attributes of the client.
Each manager groups the `plone.restapi` services for one subject, and each method returns the site's JSON answer as Python dictionaries and lists.

## Create a page

Add these lines to the end of `script.py`.

```python
from plone_client import blocks

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

Run the script again.

```shell
uv run python script.py
```

```text
Connected to Plone Site
Created http://localhost:8080/Plone/hello in state private
```

Open `http://localhost:8080/Plone/++api++/hello` in your browser, logged in as `admin`, to see the page as the site stores it.
Notice the `blocks` field: {mod}`plone_client.blocks` built the title, description, and text blocks a Volto page needs.

## Publish it

New pages are private.
Add these lines to publish it.

```python
client.workflow.transition(page["@id"], "publish")
print("Published", client.content.get(page["@id"])["review_state"])
```

The page already exists, so running the whole script again would fail when it tries to create it.
Delete the page if it is there, then create it again.

```python
if client.content.exists("/hello"):
    client.content.delete("/hello")
```

Put those lines just before the call to `client.content.create`, and run the script.

```shell
uv run python script.py
```

```text
Connected to Plone Site
Created http://localhost:8080/Plone/hello in state private
Published published
```

## Find it again

Add a search at the end of the script.

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
Created http://localhost:8080/Plone/hello in state private
Published published
Found Hello, Plone
```

`search.iter` goes through every page of results for you, however many there are.

## The complete script

```python
from plone_client import PloneClient
from plone_client import blocks

client = PloneClient("http://localhost:8080/Plone", username="admin", password="admin")
site = client.content.get("/")
print("Connected to", site["title"])

if client.content.exists("/hello"):
    client.content.delete("/hello")
page = client.content.create(
    "/",
    "Document",
    id="hello",
    title="Hello, Plone",
    description="My first page created with plone-client",
    **blocks.build(blocks.title(), blocks.description(), blocks.text("It works.")),
)
print("Created", page["@id"], "in state", page["review_state"])

client.workflow.transition(page["@id"], "publish")
print("Published", client.content.get(page["@id"])["review_state"])

for item in client.search.iter(portal_type="Document", review_state="published"):
    print("Found", item["title"])
```

You have connected to a site, created a page with blocks, published it, and found it with a search.
Stop the Plone site with {kbd}`Control-C` in its terminal when you are done; nothing it stored is kept.

## Next steps

- {ref}`tutorial-first-cli-session` does the same from the command line.
- {ref}`howto-connect` keeps the password out of your script.
- {ref}`howto-sync` turns this into a real sync from an external source.
