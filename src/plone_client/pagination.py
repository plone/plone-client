"""
Pagination helpers for plone-client.

:class:`BatchResult` wraps a single page of plone.restapi batch results
and provides convenient access to items, totals, and navigation links.

:func:`paginate` lazily iterates every page of a batched result set,
yielding individual items without loading the full catalog into memory.
"""

from __future__ import annotations

from collections.abc import Callable
from collections.abc import Generator
from collections.abc import Iterator
from typing import Any


class BatchResult:
    """
    A single page of results from a plone.restapi batch response.

    :ivar items: Items on this page.
    :vartype items: list[dict]
    :ivar items_total: Total number of matching items across all pages.
    :vartype items_total: int
    :ivar b_start: Zero-based offset of the first item on this page.
    :vartype b_start: int
    :ivar b_size: Maximum number of items per page.
    :vartype b_size: int
    :ivar next_url: URL of the next page, or ``None`` if this is the last page.
    :vartype next_url: str or None
    :ivar prev_url: URL of the previous page, or ``None`` if this is the first page.
    :vartype prev_url: str or None

    Example::

        result = BatchResult(client.search.search({"portal_type": "Document"}))
        print(f"Page 1/{result.total_pages}: {len(result.items)} items")
    """

    def __init__(self, raw: dict[str, Any]) -> None:
        self._raw = raw

    @property
    def items(self) -> list[dict[str, Any]]:
        return self._raw.get("items", [])

    @property
    def items_total(self) -> int:
        return int(self._raw.get("items_total", 0))

    @property
    def b_start(self) -> int:
        return int(self._raw.get("batching", {}).get("first", {}).get("b_start", 0))

    @property
    def b_size(self) -> int:
        size = len(self.items)
        return size if size else 25

    @property
    def next_url(self) -> str | None:
        return self._raw.get("batching", {}).get("next")

    @property
    def prev_url(self) -> str | None:
        return self._raw.get("batching", {}).get("prev")

    @property
    def total_pages(self) -> int:
        if not self.b_size:
            return 1
        import math

        return max(1, math.ceil(self.items_total / self.b_size))

    @property
    def has_next(self) -> bool:
        return self.next_url is not None

    @property
    def has_prev(self) -> bool:
        return self.prev_url is not None

    def __len__(self) -> int:
        return len(self.items)

    def __iter__(self) -> Iterator[dict[str, Any]]:
        return iter(self.items)

    def __repr__(self) -> str:
        return (
            f"BatchResult(items={len(self.items)}, "
            f"items_total={self.items_total}, "
            f"has_next={self.has_next})"
        )


def paginate(
    fetch_fn: Callable[..., dict[str, Any]],
    *,
    b_size: int = 50,
    max_items: int | None = None,
    **kwargs: Any,
) -> Generator[dict[str, Any], None, None]:
    """
    Lazily iterate items from a paginated plone.restapi endpoint.

    :param fetch_fn: Any callable that accepts ``b_size`` and ``b_start`` keyword
        arguments and returns a batch dict (``{"items": [...], "items_total": N}``).
        Typically a bound manager method such as ``client.search.search``.
    :type fetch_fn: callable
    :param b_size: Number of items to fetch per request.
    :type b_size: int
    :param max_items: Stop after this many items (``None`` = no limit).
    :type max_items: int or None
    :param kwargs: Extra keyword arguments forwarded to *fetch_fn*.
    :yields: Each individual item from the result set.
    :ytype: dict

    Example::

        for doc in paginate(client.search.search, b_size=100, portal_type="Document"):
            process(doc)

        # With a limit
        first_ten = list(paginate(client.search.search, b_size=10, max_items=10))
    """
    b_start = 0
    yielded = 0

    while True:
        raw = fetch_fn(b_size=b_size, b_start=b_start, **kwargs)
        items = raw.get("items", [])
        total = raw.get("items_total", 0)

        for item in items:
            if max_items is not None and yielded >= max_items:
                return
            yield item
            yielded += 1

        b_start += b_size
        if b_start >= total or not items:
            break
