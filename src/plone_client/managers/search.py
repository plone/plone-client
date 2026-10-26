"""Search: the ``@search`` catalog query and ``@querystring-search``."""

from .base import BaseManager
from collections.abc import Iterable
from collections.abc import Iterator
from collections.abc import Mapping
from typing import Any


class SearchManager(BaseManager):
    """Catalog queries through ``@search``.

    Searching *on* a folder restricts the results to that folder, which works
    the same with and without virtual hosting. That is why ``path`` here is
    the folder to search in, not a ``path`` index query.
    """

    def _params(
        self,
        query: Mapping[str, Any] | None,
        *,
        portal_type: str | Iterable[str] | None,
        review_state: str | Iterable[str] | None,
        text: str | None,
        depth: int | None,
        sort_on: str | Iterable[str] | None,
        sort_order: str | None,
        metadata_fields: str | Iterable[str] | None,
        fullobjects: bool,
        indexes: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Query parameters of a search.

        :returns: Parameters for :meth:`PloneClient.request`.
        """
        params: dict[str, Any] = {
            **(query or {}),
            "portal_type": portal_type,
            "review_state": review_state,
            "SearchableText": text,
            "path.depth": depth,
            "sort_on": sort_on,
            "sort_order": sort_order,
            "metadata_fields": metadata_fields,
            "fullobjects": 1 if fullobjects else None,
            **indexes,
        }
        return {key: value for key, value in params.items() if value is not None}

    def search(
        self,
        path: str = "/",
        *,
        query: Mapping[str, Any] | None = None,
        portal_type: str | Iterable[str] | None = None,
        review_state: str | Iterable[str] | None = None,
        text: str | None = None,
        depth: int | None = None,
        sort_on: str | Iterable[str] | None = None,
        sort_order: str | None = None,
        metadata_fields: str | Iterable[str] | None = None,
        fullobjects: bool = False,
        b_size: int | None = None,
        b_start: int | None = None,
        **indexes: Any,
    ) -> dict[str, Any]:
        """One page of results.

        :param path: Folder to search in; the site root by default.
        :param query: Catalog query as a mapping, for index names that are
            not valid keyword arguments; nested options are flattened
            (``{"created": {"query": "2026-01-01", "range": "min"}}``).
        :param portal_type: Content types.
        :param review_state: Workflow states.
        :param text: Full-text search (``SearchableText``).
        :param depth: Levels below ``path``: ``0`` is the folder itself,
            ``1`` its children.
        :param sort_on: Index to sort on; several sort on each in turn.
        :param sort_order: ``ascending`` or ``descending``.
        :param metadata_fields: Extra catalog metadata in each result
            (``_all`` for every column).
        :param fullobjects: Return full serializations; much slower.
        :param b_size: Results per page (the site defaults to 25).
        :param b_start: Offset of the page.
        :param indexes: Other catalog indexes, such as ``UID`` or ``Subject``.
        :returns: ``items``, ``items_total`` and ``batching``.
        """
        params = self._params(
            query,
            portal_type=portal_type,
            review_state=review_state,
            text=text,
            depth=depth,
            sort_on=sort_on,
            sort_order=sort_order,
            metadata_fields=metadata_fields,
            fullobjects=fullobjects,
            indexes=indexes,
        )
        if b_size is not None:
            params["b_size"] = b_size
        if b_start is not None:
            params["b_start"] = b_start
        return self._client.get(self._service(path, "@search"), **params)

    def iter(
        self,
        path: str = "/",
        *,
        query: Mapping[str, Any] | None = None,
        portal_type: str | Iterable[str] | None = None,
        review_state: str | Iterable[str] | None = None,
        text: str | None = None,
        depth: int | None = None,
        sort_on: str | Iterable[str] | None = None,
        sort_order: str | None = None,
        metadata_fields: str | Iterable[str] | None = None,
        fullobjects: bool = False,
        limit: int | None = None,
        b_size: int = 100,
        **indexes: Any,
    ) -> Iterator[dict[str, Any]]:
        """Every result, fetching the pages as needed.

        Takes the same arguments as :meth:`search`, plus:

        :param limit: Stop after this many results.
        :param b_size: Results fetched per request.
        :returns: Each result.
        """
        params = self._params(
            query,
            portal_type=portal_type,
            review_state=review_state,
            text=text,
            depth=depth,
            sort_on=sort_on,
            sort_order=sort_order,
            metadata_fields=metadata_fields,
            fullobjects=fullobjects,
            indexes=indexes,
        )
        params["b_size"] = b_size
        return self._client.iter_items(
            self._service(path, "@search"), params, limit=limit
        )

    def count(
        self,
        path: str = "/",
        *,
        query: Mapping[str, Any] | None = None,
        portal_type: str | Iterable[str] | None = None,
        review_state: str | Iterable[str] | None = None,
        text: str | None = None,
        depth: int | None = None,
        **indexes: Any,
    ) -> int:
        """Number of results of a search.

        :returns: ``items_total``.
        """
        page = self.search(
            path,
            query=query,
            portal_type=portal_type,
            review_state=review_state,
            text=text,
            depth=depth,
            b_size=1,
            **indexes,
        )
        return int(page.get("items_total", 0))


class QuerystringManager(BaseManager):
    """Collection-style queries through ``@querystring-search``."""

    def config(self, path: str = "/") -> dict[str, Any]:
        """Indexes, operators and sort options the querystring accepts.

        :param path: Context of the query.
        :returns: ``indexes`` and ``sortable_indexes``.
        """
        return self._client.get(self._service(path, "@querystring"))

    def search(
        self,
        query: Iterable[Mapping[str, Any]],
        *,
        path: str = "/",
        sort_on: str | None = None,
        sort_order: str | None = None,
        limit: int | None = None,
        b_size: int | None = None,
        b_start: int | None = None,
        metadata_fields: str | Iterable[str] | None = None,
        fullobjects: bool = False,
    ) -> dict[str, Any]:
        """Run a querystring query.

        :param query: Criteria, each with ``i`` (index), ``o`` (operation)
            and ``v`` (value), as a Listing block stores them.
        :param path: Context of the query, for relative path criteria.
        :param sort_on: Index to sort on.
        :param sort_order: ``ascending`` or ``descending``.
        :param limit: Maximum number of results.
        :param b_size: Results per page.
        :param b_start: Offset of the page.
        :param metadata_fields: Extra catalog metadata in each result.
        :param fullobjects: Return full serializations.
        :returns: ``items``, ``items_total`` and ``batching``.
        """
        body: dict[str, Any] = {
            "query": [dict(criterion) for criterion in query],
            "sort_on": sort_on,
            "sort_order": sort_order,
            "limit": limit,
            "b_size": b_size,
            "b_start": b_start,
            "fullobjects": True if fullobjects else None,
        }
        if metadata_fields is not None:
            body["metadata_fields"] = (
                [metadata_fields]
                if isinstance(metadata_fields, str)
                else list(metadata_fields)
            )
        body = {key: value for key, value in body.items() if value is not None}
        return self._client.post(self._service(path, "@querystring-search"), body)
