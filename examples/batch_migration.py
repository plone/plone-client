"""
examples/batch_migration.py
===========================
Demonstrates how to migrate content from one Plone site to another,
using the lazy ``search.iterate()`` to page through large catalogs
without loading everything into memory.

Run:
    python examples/batch_migration.py
"""

from __future__ import annotations

from plone_client import PloneClient
from plone_client import setup_logging

import logging


setup_logging(level=logging.INFO)


SOURCE_URL = "http://source.plone.site"
TARGET_URL = "http://target.plone.site"
CREDENTIALS = {"username": "admin", "password": "admin"}


def migrate_news_items() -> None:
    with (
        PloneClient(SOURCE_URL, **CREDENTIALS) as source,
        PloneClient(TARGET_URL, **CREDENTIALS) as target,
    ):
        total = 0
        errors = 0

        for item in source.search.iterate(
            {"portal_type": "News Item"},
            sort_on="created",
        ):
            # Get the full object from source
            src_path = item["@id"].replace(source.config.base_url, "")
            try:
                obj = source.content.get(src_path)
            except Exception as exc:
                logging.warning("Could not fetch %s: %s", src_path, exc)
                errors += 1
                continue

            # Determine destination container
            # e.g. /news/2024 → /news/2024
            container = "/".join(src_path.split("/")[:-1]) or "/"

            try:
                target.content.create(
                    container,
                    obj["@type"],
                    title=obj["title"],
                    description=obj.get("description", ""),
                    text=obj.get("text"),
                    subjects=obj.get("subjects", []),
                )
                total += 1
                logging.info("Migrated: %s", src_path)
            except Exception as exc:
                logging.warning("Failed to create %s: %s", src_path, exc)
                errors += 1

        print(f"\nMigration complete: {total} items migrated, {errors} errors")


if __name__ == "__main__":
    migrate_news_items()
