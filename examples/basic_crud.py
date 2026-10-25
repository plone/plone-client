"""
examples/basic_crud.py
======================
Demonstrates basic content CRUD, search, and workflow operations.

Run:
    PLONE_CLIENT_BASE_URL=http://localhost:8080/Plone \
    PLONE_CLIENT_USERNAME=admin \
    PLONE_CLIENT_PASSWORD=admin \
    python examples/basic_crud.py
"""

from __future__ import annotations

from plone_client import PloneClient
from plone_client import setup_logging

import logging


# Optional: see every HTTP request/response
setup_logging(level=logging.DEBUG)


def main() -> None:
    # All config from env vars — no credentials in code
    with PloneClient() as client:
        # ── Site info ────────────────────────────────────────────────
        info = client.site.info()
        print(f"Connected to: {info.get('title', '?')} ({info['@id']})")

        # ── Create a Document ────────────────────────────────────────
        doc = client.content.create(
            "/",
            "Document",
            title="My First Document",
            description="Created by plone-client",
        )
        doc_path = doc["@id"].replace(client.config.base_url, "")
        print(f"Created: {doc_path}")

        # ── Read it back ─────────────────────────────────────────────
        fetched = client.content.get(doc_path)
        assert fetched["title"] == "My First Document"
        print(f"Read:    {fetched['title']}")

        # ── Update ───────────────────────────────────────────────────
        updated = client.content.update(doc_path, description="Updated description")
        print(f"Updated: {updated['description']}")

        # ── Workflow: publish ─────────────────────────────────────────
        workflow = client.content.workflow(doc_path)
        transitions = [t["@id"].split("/")[-1] for t in workflow.get("transitions", [])]
        print(f"Available transitions: {transitions}")
        if "publish" in transitions:
            result = client.content.transition(doc_path, "publish")
            print(f"Published: review_state={result.get('review_state', '?')}")

        # ── Search ───────────────────────────────────────────────────
        results = client.search.search(
            {
                "portal_type": "Document",
                "sort_on": "created",
                "sort_order": "descending",
            },
            b_size=5,
        )
        print(f"Search found {results['items_total']} documents")

        # ── Clean up ─────────────────────────────────────────────────
        client.content.delete(doc_path)
        print(f"Deleted: {doc_path}")


if __name__ == "__main__":
    main()
