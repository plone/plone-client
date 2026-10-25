"""
Relations manager — ``@relations`` endpoint.

plone.restapi exposes relation creation, listing, and deletion through
``@relations`` on the site root and on individual content objects.
"""

from __future__ import annotations

from .base import BaseManager
from typing import Any


class RelationsManager(BaseManager):
    """
    Manage content relations (``relatedItems``, custom relation fields, etc.)

    The ``@relations`` endpoint was introduced in plone.restapi 8.x / Plone 6.
    On older Plone installations, use the ``relatedItems`` field via
    :meth:`~plone_client.managers.content.ContentManager.update` instead.
    """

    # ------------------------------------------------------------------
    # Site-root level
    # ------------------------------------------------------------------

    def list(
        self,
        relation: str | None = None,
        source: str | None = None,
        target: str | None = None,
        b_size: int = 25,
        b_start: int = 0,
    ) -> dict[str, Any]:
        """
        List all relations, optionally filtered.

        :param relation: Relation name, e.g. ``"relatedItems"``.
        :type relation: str or None
        :param source: UID or path of the source object.
        :type source: str or None
        :param target: UID or path of the target object.
        :type target: str or None
        :param b_size: Batch size.
        :type b_size: int
        :param b_start: Batch start offset.
        :type b_start: int
        """
        params: dict[str, Any] = {"b_size": b_size, "b_start": b_start}
        if relation:
            params["relation"] = relation
        if source:
            params["source"] = source
        if target:
            params["target"] = target
        return self._get("/@relations", params=params)

    def create(
        self,
        source: str,
        target: str,
        relation: str = "relatedItems",
    ) -> dict[str, Any]:
        """
        Create a relation between *source* and *target*.

        :param source: Path or UID of the source object.
        :type source: str
        :param target: Path or UID of the target object.
        :type target: str
        :param relation: Relation name.
        :type relation: str
        """
        return self._post(
            "/@relations",
            json={"source": source, "target": target, "relation": relation},
        )

    def delete(
        self,
        source: str,
        target: str,
        relation: str = "relatedItems",
    ) -> None:
        """Remove a relation between *source* and *target*."""
        self._conn.delete(
            "/@relations",
            json={"source": source, "target": target, "relation": relation},
        )

    def rebuild(self) -> dict[str, Any]:
        """Rebuild the relations catalog (``POST /@relations`` with ``rebuild``)."""
        return self._post("/@relations", json={"rebuild": True})

    # ------------------------------------------------------------------
    # Object-level
    # ------------------------------------------------------------------

    def get_for(self, path: str) -> dict[str, Any]:
        """Return all relations defined on a specific content object."""
        return self._get(f"{path}/@relations")

    def stats(self) -> dict[str, Any]:
        """Return relation statistics from ``/@relationstats``."""
        return self._get("/@relationstats")

    def broken(self) -> dict[str, Any]:
        """List broken relations from ``/@brokenrelations``."""
        return self._get("/@brokenrelations")
