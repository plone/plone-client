---
myst:
  html_meta:
    "description": "Copy news items and their images from one place to another with a Python script: rehearse with a dry run, recover from a failure, and verify by counting."
    "property=og:description": "Copy news items and their images from one place to another with a Python script: rehearse with a dry run, recover from a failure, and verify by counting."
    "property=og:title": "Migrate content between two sites"
---

(tutorial-migrate)=

# Migrate content between two sites

In this tutorial, we will write a script that copies news items and their images from a source to a target.
We will rehearse it with a {term}`dry run`, watch it fail part way and recover, and verify the result by counting.
At the end, you will have a migration script that you can run again safely, because it skips what is already there.

To keep the tutorial light on your computer, we will run one {term}`Plone` site, with the folders `/source` and `/target` standing for the two sites.
The script has two clients, so moving to two real sites means changing two URLs.

You need [uv](https://docs.astral.sh/uv/) and [Docker](https://www.docker.com/), and you should have followed {ref}`tutorial-first-script`.

<!-- check: start -->

## Start a Plone site

Get the Compose file, and start the site.

<!-- check: skip -->
```shell
curl -O https://raw.githubusercontent.com/plone/plone-client/main/docker-compose.yml
docker compose up --wait
```

Open `http://localhost:3000` to see it, with the user `admin` and the password `admin`.
These credentials belong to the throwaway {term}`Compose site`; never reuse them on a real site.
{ref}`howto-run-a-site` explains what it has.

## Prepare the source

Create a project.

<!-- check: skip -->
```shell
uv init --bare migration
cd migration
uv add plone-client
```

Create a file named `prepare.py`, which creates the two folders and three news items, each with a {term}`lead image` stored inside it.

<!-- check: file prepare.py -->
```python
from pathlib import Path
from plone_client import blocks
from plone_client import operations
from plone_client import PloneClient

import base64


PIXEL = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR4nGNgaPgPAAIDAYBB0fBwAAAAAElFTkSuQmCC"
NEWS = [
    ("spring", "Spring meeting", "We met in April."),
    ("summer", "Summer sprint", "We wrote code in July."),
    ("autumn", "Autumn release", "The release came out in October."),
]

Path("photo.png").write_bytes(base64.b64decode(PIXEL))
with PloneClient("http://localhost:8080/Plone", username="admin", password="admin") as site:
    for name in ("source", "target"):
        site.content.create("/", "Document", id=name, title=name.title())
        site.workflow.transition(f"/{name}", "publish")
    for item_id, title, description in NEWS:
        operations.create_with_files(
            site,
            "/source",
            "News Item",
            ["photo.png"],
            id=item_id,
            title=title,
            description=description,
            publish="publish",
        )
print("prepared")
```

```shell
uv run python prepare.py
```

```text
prepared
```

## Read the source

Create a file named `migrate.py`.
The source client is {term}`read-only`, so nothing in this script can change the source by mistake.
`records` reads what a news item needs: its fields, and the images inside it.

<!-- check: file migrate.py -->
```python
from pathlib import Path
from plone_client import operations
from plone_client import PloneClient
from plone_client import PloneOperationError

import sys
import tempfile


URL = "http://localhost:8080/Plone"
AUTH = {"username": "admin", "password": "admin"}
FIELDS = ("title", "description", "subjects", "blocks", "blocks_layout")
TRANSITION = "publish"
SOURCE = "/source"
TARGET = "/target"


def records(source):
    for entry in source.search.iter(SOURCE, portal_type="News Item", sort_on="sortable_title"):
        item = source.content.get(entry["@id"], include_items=False)
        images = list(source.content.children(entry["@id"], portal_type="Image"))
        yield item, images


def copy_item(source, target, item, images, folder):
    files = []
    for image in images:
        path = Path(folder) / image["@id"].rsplit("/", 1)[-1]
        path.write_bytes(source.files.download(image["@id"], field="image"))
        files.append(path)
    data = {name: item[name] for name in FIELDS if item.get(name)}
    return operations.create_with_files(
        target, TARGET, "News Item", files, data=data, id=item["id"], publish=TRANSITION
    )


def main():
    apply = "--apply" in sys.argv
    with (
        PloneClient(URL, read_only=True, **AUTH) as source,
        PloneClient(URL, dry_run=not apply, **AUTH) as target,
        tempfile.TemporaryDirectory() as folder,
    ):
        for item, images in records(source):
            if target.exists(f"{TARGET}/{item['id']}"):
                print("skip", item["id"])
                continue
            try:
                result = copy_item(source, target, item, images, folder)
            except PloneOperationError as error:
                print("FAILED", item["id"], error.result.error["message"])
                for created in reversed(error.result.created):
                    print("  left behind:", created["@id"])
                return 1
            print("copy", item["id"], len(result.created), "items,", len(result.requests), "requests")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Notice that the script uses {func}`~plone_client.operations.create_with_files` on the target: it finds where this site keeps the lead image, which may differ from the source.

```{note}
Internal links inside blocks point to the source.
Rewrite them if the two sites have different paths: {func}`~plone_client.blocks.iter_links` finds them.
```

## Rehearse with a dry run

Run it without `--apply`.
The target client records its changes and sends none.

```shell
uv run python migrate.py
```

```text
copy autumn 2 items, 7 requests
copy spring 2 items, 7 requests
copy summer 2 items, 7 requests
```

Each item takes one `GET` of its type and four changes: the item, the image, the lead image, and the transition.
Check that the target is still empty.

<!-- check: file count.py -->
```python
from plone_client import PloneClient

with PloneClient("http://localhost:8080/Plone", username="admin", password="admin") as site:
    for name in ("/source", "/target"):
        news = site.search.count(name, portal_type="News Item")
        images = site.search.count(name, portal_type="Image")
        published = site.search.count(name, portal_type="News Item", review_state="published")
        print(name, news, "news items,", images, "images,", published, "published")
```

```shell
uv run python count.py
```

```text
/source 3 news items, 3 images, 3 published
/target 0 news items, 0 images, 0 published
```

## Watch it fail

Real migrations stop part way.
Make this one stop with a typing mistake in the name of the {term}`transition`.

```shell
sed -i.bak 's/TRANSITION = "publish"/TRANSITION = "publsh"/' migrate.py
```

<!-- check: exit 1 -->
```shell
uv run python migrate.py --apply
```

```text
FAILED autumn No workflow provides the '${action_id}' action.
  left behind: http://localhost:8080/Plone/target/autumn/photo.png
  left behind: http://localhost:8080/Plone/target/autumn
```

The site refused the transition.
By then, the item and its image existed, and {class}`~plone_client.exceptions.PloneOperationError` carries a `result` that says so, so the script can name what it left behind.

## Recover

Delete what the failure left, and correct the mistake.
Deleting the news item also deletes the image inside it.

<!-- check: file clean.py -->
```python
from plone_client import PloneClient

with PloneClient("http://localhost:8080/Plone", username="admin", password="admin") as site:
    site.content.delete("/target/autumn")
print("cleaned")
```

```shell
uv run python clean.py
sed -i.bak 's/TRANSITION = "publsh"/TRANSITION = "publish"/' migrate.py
```

```text
cleaned
```

## Migrate

Run it for real.

```shell
uv run python migrate.py --apply
```

```text
copy autumn 2 items, 6 requests
copy spring 2 items, 6 requests
copy summer 2 items, 6 requests
```

Run it again.

```shell
uv run python migrate.py --apply
```

```text
skip autumn
skip spring
skip summer
```

Notice that the second run skipped everything, which is what lets you run a migration again after any failure.

## Verify by counting

```shell
uv run python count.py
```

```text
/source 3 news items, 3 images, 3 published
/target 3 news items, 3 images, 3 published
```

The two lines match.
Check one lead image as well.

<!-- check: file lead.py -->
```python
from plone_client import PloneClient

with PloneClient("http://localhost:8080/Plone", username="admin", password="admin") as site:
    item = site.content.get("/target/summer")
    print(item["review_state"], item["preview_image_link"]["@id"])
```

```shell
uv run python lead.py
```

```text
published http://localhost:8080/Plone/target/summer/photo.png
```

The link points to the copy inside the target, not to the source.

You have rehearsed a migration, recovered from a failure, and proved the result, with a script that is safe to run again.

## Move to two real sites

Change the `URL` and `AUTH` of each client, and the paths of `SOURCE` and `TARGET`.
Give each site a {term}`profile`, and use `PloneClient.from_profile("source", read_only=True)` to keep passwords out of the script.

## Clean up

<!-- check: skip -->
```shell
docker compose down -v
```

If a step failed, `docker compose down -v` still resets the site; then start again from the top.

<!-- check: stop -->

## Next steps

- {ref}`howto-large-sites` keeps a migration fast on large sites.
- {ref}`reference-operations` explains the result of an operation.
- {ref}`howto-troubleshoot` helps when something does not work.
