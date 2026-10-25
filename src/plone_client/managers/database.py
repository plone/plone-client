"""
Database & maintenance manager.

Covers endpoints typically used for operational / DevOps tasks:
- ``@database``          — ZODB stats
- ``@pack-database``     — ZODB pack
- ``@reindex``           — full catalog reindex
- ``@catalog-rebuild``   — rebuild catalog
- ``@sources``           — catalog sources
- ``@linkintegrity``     — link integrity check
- ``@unused-uids``       — find objects with broken UIDs
- ``@object-provides``   — list interfaces provided by an object
- ``@typesinfo``         — extended type information
"""

from __future__ import annotations

from .base import BaseManager
from typing import Any


class DatabaseManager(BaseManager):
    """
    Operational endpoints for Plone administrators.

    All methods require Manager-level permissions.
    """

    # ------------------------------------------------------------------
    # ZODB
    # ------------------------------------------------------------------

    def info(self) -> dict[str, Any]:
        """Return ZODB database statistics (``@database``)."""
        return self._get("/@database")

    def pack(self, days: int = 0) -> dict[str, Any]:
        """
        Pack the ZODB database.

        :param days: Keep transactions newer than this many days
            (default 0 = full pack).
        :type days: int
        """
        return self._post("/@pack-database", json={"days": days})

    # ------------------------------------------------------------------
    # Catalog
    # ------------------------------------------------------------------

    def reindex(self) -> dict[str, Any]:
        """Trigger a full catalog reindex (``@reindex``)."""
        return self._post("/@reindex")

    def rebuild_catalog(self) -> dict[str, Any]:
        """Rebuild the entire catalog from scratch (``@catalog-rebuild``)."""
        return self._post("/@catalog-rebuild")

    def catalog_sources(self) -> dict[str, Any]:
        """Return available catalog sources (``@sources``)."""
        return self._get("/@sources")

    # ------------------------------------------------------------------
    # Integrity
    # ------------------------------------------------------------------

    def link_integrity(self, path: str) -> dict[str, Any]:
        """
        Check link integrity for *path*.

        Returns objects that would become broken if *path* were deleted.
        """
        return self._get(f"{path}/@linkintegrity")

    def unused_uids(self) -> dict[str, Any]:
        """Find content objects with broken / orphaned UIDs."""
        return self._get("/@unused-uids")

    # ------------------------------------------------------------------
    # Introspection
    # ------------------------------------------------------------------

    def object_provides(self, path: str) -> list[str]:
        """Return a list of interface dotted names provided by the object at *path*."""
        return self._get(f"{path}/@object-provides")

    def types_info(self) -> dict[str, Any]:
        """Return extended type information (``@typesinfo``)."""
        return self._get("/@typesinfo")
