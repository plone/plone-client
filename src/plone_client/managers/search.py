"""Search manager — wraps ``@search`` and ``@querystring*`` endpoints."""

from __future__ import annotations

from .base import BaseManager
from typing import Any


class SearchManager(BaseManager):
    """Query Plone's catalog via plone.restapi search endpoints."""

    def search(
        self,
        query: dict[str, Any] | None = None,
        *,
        path: str = "/",
        sort_on: str | None = None,
        sort_order: str = "ascending",
        b_size: int = 25,
        b_start: int = 0,
        fullobjects: bool = False,
        **extra_params: Any,
    ) -> dict[str, Any]:
        """
        Perform a catalog search.

        :param query: Dict of catalog indexes and their query values, e.g.
            ``{"portal_type": "Document", "review_state": "published"}``.
        :type query: dict or None
        :param path: Scope the search to this path.
        :type path: str
        :param sort_on: Catalog index to sort on.
        :type sort_on: str or None
        :param sort_order: ``"ascending"`` or ``"descending"``.
        :type sort_order: str
        :param b_size: Batch size.
        :type b_size: int
        :param b_start: Batch start offset.
        :type b_start: int
        :param fullobjects: Return full object representations instead of metadata.
        :type fullobjects: bool
        :param extra_params: Any additional catalog query parameters.
        """
        params: dict[str, Any] = {
            "b_size": b_size,
            "b_start": b_start,
        }

        if query:
            params.update(query)

        if path != "/":
            params["path.query"] = path
            params["path.depth"] = -1

        if sort_on:
            params["sort_on"] = sort_on
            params["sort_order"] = sort_order

        if fullobjects:
            params["fullobjects"] = 1

        params.update(extra_params)

        return self._get("/@search", params=params)

    def querystring(self, query: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        """
        Execute a ``@querystring-search`` query (Collection-style).

        :param query: List of query records as expected by ``plone.app.querystring``,
            e.g.::

                [
                    {
                        "i": "portal_type",
                        "o": "plone.app.querystring.operation.selection.any",
                        "v": ["Document"],
                    }
                ]
        :type query: list[dict]
        :param kwargs: Additional parameters (sort_on, sort_order, b_size, b_start,
            fullobjects, …).
        """
        payload = {"query": query}
        payload.update(kwargs)
        return self._post("/@querystring-search", json=payload)

    def querystring_options(self) -> dict[str, Any]:
        """Return available querystring indexes and operations."""
        return self._get("/@querystring")

    def iterate(
        self,
        query: dict[str, Any] | None = None,
        *,
        path: str = "/",
        b_size: int = 50,
        **extra_params: Any,
    ):
        """
        Lazily iterate over all search results, handling batching automatically.

        :yields: Each item from the search results.
        :ytype: dict
        """
        b_start = 0
        while True:
            result = self.search(
                query,
                path=path,
                b_size=b_size,
                b_start=b_start,
                **extra_params,
            )
            items = result.get("items", [])
            yield from items

            total = result.get("items_total", 0)
            b_start += b_size
            if b_start >= total:
                break
