"""Publish a news item, with a lead image, from a text file.

The first line of the text file is the title, the second the description,
and each later paragraph becomes a text block. Without ``--apply``, the
script only reports what it would send.

Sites differ in how a news item holds its lead image: Plone 6.1 sites
created for Volto link to an image with ``preview_image_link``, while others
store it in an ``image`` field. The script reads the content type's schema
and does whichever the site expects.

Usage::

    python docs/_examples/publish_news.py news.txt /news --image lead.jpg
    python docs/_examples/publish_news.py news.txt /news --image lead.jpg --apply
"""

from pathlib import Path
from plone_client import blocks
from plone_client import file_data
from plone_client import PloneClient
from plone_client import PloneClientError
from typing import Any

import argparse
import json
import sys


def news_data(source: Path) -> dict[str, Any]:
    """Field values of the news item.

    :param source: Text file: title, description, then paragraphs.
    :returns: The fields, blocks included.
    """
    title, description, *rest = source.read_text().split("\n")
    paragraphs = [p.strip() for p in "\n".join(rest).split("\n\n") if p.strip()]
    return {
        "title": title.strip(),
        "description": description.strip(),
        **blocks.build(
            blocks.title(),
            blocks.description(),
            *(blocks.text(paragraph) for paragraph in paragraphs),
        ),
    }


def publish(
    client: PloneClient, folder: str, data: dict[str, Any], image: Path | None
) -> dict[str, Any]:
    """Create the news item, attach its lead image, and publish it.

    :param client: Client of the site.
    :param folder: Path of the folder.
    :param data: Field values of the news item.
    :param image: Lead image, if any.
    :returns: The news item, or the skipped request in a dry run.
    """
    fields = client.types.get("News Item")["properties"]
    if image and "image" in fields:
        data = {**data, "image": file_data(image)}
    item = client.content.create(folder, "News Item", data)
    if client.dry_run:
        # Nothing was created, so there is nothing to attach or publish yet.
        return item
    if image and "image" not in fields and "preview_image_link" in fields:
        lead = client.files.upload(item["@id"], image)
        client.content.update(
            item["@id"], preview_image_link=lead["UID"], representation=False
        )
    client.workflow.transition(item["@id"], "publish")
    return item


def main() -> int:
    """Run the script.

    :returns: The exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("source", type=Path, help="Text file with the news")
    parser.add_argument("folder", help="Path of the folder in the site")
    parser.add_argument("--image", type=Path, help="Lead image")
    parser.add_argument("--profile", help="Profile to use, instead of $PLONE_CLIENT_*")
    parser.add_argument("--apply", action="store_true", help="Change the site")
    args = parser.parse_args()

    settings = {"dry_run": not args.apply}
    try:
        if args.profile:
            client = PloneClient.from_profile(args.profile, **settings)
        else:
            client = PloneClient.from_env(**settings)
        with client:
            item = publish(client, args.folder, news_data(args.source), args.image)
            log = client.dry_run_log
    except PloneClientError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    if not args.apply:
        for entry in log:
            entry.get("json", {}).get("image", {}).pop("data", None)
            print(json.dumps(entry, indent=2, ensure_ascii=False))
        print("Dry run: nothing was changed")
        return 0
    print(f"Published {item['@id']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
