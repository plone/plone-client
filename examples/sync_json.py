"""Sync records from a JSON file into a Plone folder.

Each record becomes a page in the folder, named after the record's ``id``.
Running the script again updates the pages whose records changed, and
``--prune`` deletes the pages whose records are gone. Without ``--apply``,
the script only reports what it would do.

The records file holds a list of objects::

    [
        {"id": "plone-6-2", "title": "Plone 6.2", "description": "…",
         "text": "Plone 6.2 is out.", "subjects": ["release"]}
    ]

Usage::

    python examples/sync_json.py records.json /news/releases
    python examples/sync_json.py records.json /news/releases --apply --prune
    python examples/sync_json.py records.json /news/releases --profile local --apply
"""

from pathlib import Path
from plone_client import PloneClient
from plone_client import PloneClientError
from plone_client import blocks
from typing import Any

import argparse
import json
import sys


FIELDS = ("title", "description", "subjects")


def item_id(entry: dict[str, Any]) -> str:
    """Id of a folder entry, the last segment of its URL.

    :param entry: A catalog entry from ``@search``.
    :returns: The item's id.
    """
    return entry["@id"].rstrip("/").rsplit("/", 1)[-1]


def page_data(record: dict[str, Any]) -> dict[str, Any]:
    """Field values of the page for a record.

    :param record: A record from the source.
    :returns: The fields, blocks included.
    """
    data = {field: record[field] for field in FIELDS if field in record}
    data.update(
        blocks.build(blocks.title(), blocks.description(), blocks.text(record["text"]))
    )
    return data


def changed(current: dict[str, Any], record: dict[str, Any]) -> bool:
    """Whether a page differs from its record, comparing the plain fields.

    :param current: The page, as returned by the site.
    :param record: The record from the source.
    :returns: ``True`` when the page needs an update.
    """
    return any(current.get(field) != record.get(field) for field in FIELDS)


def sync(
    client: PloneClient, records: list[dict[str, Any]], folder: str, prune: bool
) -> dict[str, int]:
    """Make the folder match the records.

    :param client: Client of the site.
    :param records: Records from the source.
    :param folder: Path of the folder.
    :param prune: Delete pages whose records are gone.
    :returns: How many pages were created, updated, deleted and left alone.
    """
    existing = {
        item_id(entry): entry
        for entry in client.content.children(folder, portal_type="Document")
    }
    counts = {"created": 0, "updated": 0, "deleted": 0, "unchanged": 0}
    for record in records:
        entry = existing.pop(record["id"], None)
        if entry is None:
            client.content.create(folder, "Document", id=record["id"], **page_data(record))
            print(f"+ {record['id']}")
            counts["created"] += 1
        elif changed(client.content.get(entry["@id"], include_items=False), record):
            client.content.update(entry["@id"], page_data(record), representation=False)
            print(f"~ {record['id']}")
            counts["updated"] += 1
        else:
            counts["unchanged"] += 1
    if prune:
        for name, entry in existing.items():
            client.content.delete(entry["@id"])
            print(f"- {name}")
            counts["deleted"] += 1
    return counts


def main() -> int:
    """Run the script.

    :returns: The exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("records", type=Path, help="JSON file with the records")
    parser.add_argument("folder", help="Path of the folder in the site")
    parser.add_argument("--profile", help="Profile to use, instead of $PLONE_CLIENT_*")
    parser.add_argument("--prune", action="store_true", help="Delete stale pages")
    parser.add_argument("--apply", action="store_true", help="Change the site")
    args = parser.parse_args()

    records = json.loads(args.records.read_text())
    settings = {"dry_run": not args.apply}
    try:
        if args.profile:
            client = PloneClient.from_profile(args.profile, **settings)
        else:
            client = PloneClient.from_env(**settings)
        with client:
            counts = sync(client, records, args.folder, args.prune)
    except PloneClientError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1
    summary = ", ".join(f"{count} {name}" for name, count in counts.items())
    print(summary if args.apply else f"{summary} (dry run: nothing was changed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
