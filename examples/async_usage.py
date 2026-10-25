"""
examples/async_usage.py
=======================
Demonstrates using AsyncPloneClient for concurrent operations.

Requires the async extra:
    pip install plone-client[async]

Run:
    python examples/async_usage.py
"""

from __future__ import annotations

from plone_client import setup_logging
from plone_client.async_client import AsyncPloneClient

import asyncio
import logging


setup_logging(level=logging.INFO)

BASE_URL = "http://localhost:8080/Plone"


async def fetch_multiple_pages(
    client: AsyncPloneClient, paths: list[str]
) -> list[dict]:
    """Fetch multiple pages concurrently."""
    tasks = [client.content.get(path) for path in paths]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    pages = []
    for path, result in zip(paths, results):
        if isinstance(result, Exception):
            logging.warning("Failed to fetch %s: %s", path, result)
        else:
            pages.append(result)
    return pages


async def main() -> None:
    async with AsyncPloneClient(
        BASE_URL,
        username="admin",
        password="admin",
    ) as client:
        # ── Async search ──────────────────────────────────────────────
        results = await client.search.search({"portal_type": "Document"}, b_size=10)
        print(f"Found {results['items_total']} documents")

        # ── Concurrent fetches using async iterate ────────────────────
        paths = [
            item["@id"].replace(BASE_URL, "")
            async for item in client.search.iterate(
                {"portal_type": "Document"}, b_size=5
            )
        ]
        print(f"Iterating {len(paths)} documents lazily")

        # ── Fetch first 5 concurrently ────────────────────────────────
        if paths:
            pages = await fetch_multiple_pages(client, paths[:5])
            print(f"Fetched {len(pages)} pages concurrently:")
            for page in pages:
                print(f"  - {page.get('title', '?')}")

        # ── Create, update, delete ─────────────────────────────────────
        doc = await client.content.create("/", "Document", title="Async Test")
        doc_path = doc["@id"].replace(BASE_URL, "")
        print(f"Created: {doc_path}")

        await client.content.update(doc_path, description="Updated via async")
        await client.content.delete(doc_path)
        print("Cleaned up")

        # ── Raw escape hatch ───────────────────────────────────────────
        response = await client.request("GET", "/@search", params={"b_size": 1})
        data = response.json()
        print(f"Escape hatch: items_total={data.get('items_total')}")


if __name__ == "__main__":
    asyncio.run(main())
