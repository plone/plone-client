# /// script
# requires-python = ">=3.11"
# dependencies = ["plone-client"]
# ///
"""Create the sample content that the tutorials and how-to guides assume.

Run it on a new site with ``docker compose up``, or by hand with the
``PLONE_CLIENT_*`` environment variables set. It skips what already exists, so
it can run any number of times.
"""

from plone_client import PloneClient
from typing import Any

import struct
import zlib


#: Parent, type, id, title, description, and workflow transition.
ITEMS: list[tuple[str, str, str, str, str, str | None]] = [
    ("/", "Document", "news", "News", "What is new on this site.", "publish"),
    ("/", "Document", "about", "About", "Who we are.", "publish"),
    ("/about", "Document", "team", "Team", "The people behind the site.", None),
    ("/", "Document", "media", "Media", "Images and files.", "publish"),
    (
        "/news",
        "News Item",
        "release-6-2",
        "Release 6.2 is out",
        "The new version is ready.",
        "publish",
    ),
    (
        "/news",
        "News Item",
        "release-party",
        "Release party in Brasília",
        "Join us to celebrate.",
        None,
    ),
    (
        "/news",
        "News Item",
        "release-notes-draft",
        "Release notes draft",
        "Everything that changed.",
        None,
    ),
    (
        "/news",
        "News Item",
        "sprint-report",
        "Sprint report",
        "What the sprint achieved.",
        "submit",
    ),
    (
        "/news",
        "News Item",
        "old-announcement",
        "Old announcement",
        "This one is no longer current.",
        "publish",
    ),
]


def png(red: int, green: int, blue: int, size: int = 64) -> bytes:
    """A square PNG of one color, so that the script needs no sample files.

    :param red: Red component.
    :param green: Green component.
    :param blue: Blue component.
    :param size: Width and height in pixels.
    :returns: The PNG file.
    """

    def chunk(kind: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(kind + data)
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)

    row = b"\x00" + bytes([red, green, blue]) * size
    header = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(row * size))
        + chunk(b"IEND", b"")
    )


def seed_items(site: PloneClient) -> None:
    """Create the pages and news items, in their workflow states.

    :param site: The client.
    """
    for parent, portal_type, item_id, title, description, transition in ITEMS:
        path = f"{parent.rstrip('/')}/{item_id}"
        if site.exists(path):
            print(f"exists  {path}")
            continue
        site.content.create(
            parent, portal_type, id=item_id, title=title, description=description
        )
        if transition:
            site.workflow.transition(path, transition)
        print(f"created {path}")


def seed_files(site: PloneClient) -> None:
    """Create an image and a file in ``/media``.

    :param site: The client.
    """
    files: list[tuple[str, bytes, dict[str, Any]]] = [
        ("logo.png", png(0, 131, 190), {"title": "Logo"}),
        ("readme.txt", b"Sample file.\n", {"title": "Read me"}),
    ]
    for name, data, fields in files:
        path = f"/media/{name}"
        if site.exists(path):
            print(f"exists  {path}")
            continue
        site.files.upload("/media", data, filename=name, id=name, **fields)
        print(f"created {path}")


def seed_people(site: PloneClient) -> None:
    """Create a user and a group that holds them.

    :param site: The client.
    """
    if not any(user["id"] == "jdoe" for user in site.users.list()):
        site.users.create(
            "jdoe",
            email="jdoe@example.org",
            fullname="Jo Doe",
            password="correct-horse-battery",
            roles=["Member"],
        )
        print("created user jdoe")
    if not any(group["id"] == "editors" for group in site.groups.list()):
        site.groups.create("editors", title="Editors", roles=["Editor"], users=["jdoe"])
        print("created group editors")


def main() -> None:
    """Seed the site named by the environment."""
    with PloneClient.from_env() as site:
        seed_items(site)
        seed_files(site)
        seed_people(site)
    print("seed finished")


if __name__ == "__main__":
    main()
