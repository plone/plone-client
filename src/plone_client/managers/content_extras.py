"""
Comments, versioning (CMFEditions), and tiles managers.
"""

from __future__ import annotations

from .base import BaseManager
from typing import Any


class CommentsManager(BaseManager):
    """Manage content comments via ``@comments``."""

    def list(self, path: str) -> dict[str, Any]:
        """List comments on *path*."""
        return self._get(f"{path}/@comments")

    def add(self, path: str, text: str) -> dict[str, Any]:
        """Post a new comment on *path*."""
        return self._post(f"{path}/@comments", json={"text": text})

    def update(self, path: str, comment_id: str, text: str) -> dict[str, Any]:
        """Edit comment *comment_id* on *path*."""
        return self._patch(f"{path}/@comments/{comment_id}", json={"text": text})

    def delete(self, path: str, comment_id: str) -> None:
        """Delete comment *comment_id* on *path*."""
        self._delete(f"{path}/@comments/{comment_id}")


class HistoryManager(BaseManager):
    """Access CMFEditions version history via ``@history``."""

    def list(self, path: str) -> list[dict[str, Any]]:
        """Return the version history for *path*."""
        return self._get(f"{path}/@history")

    def revert(self, path: str, version: int) -> dict[str, Any]:
        """
        Revert *path* to *version*.

        :param path: Path to the content object.
        :type path: str
        :param version: Integer version id (0 = oldest).
        :type version: int
        """
        return self._patch(f"{path}/@history", json={"version": version})


class TilesManager(BaseManager):
    """Work with Plone tiles (``@tiles``)."""

    def list(self, path: str) -> dict[str, Any]:
        """List available tile types for *path*."""
        return self._get(f"{path}/@tiles")

    def get(self, path: str, tile_type: str, tile_id: str) -> dict[str, Any]:
        """Fetch a specific tile instance."""
        return self._get(f"{path}/@tiles/{tile_type}/{tile_id}")

    def create(
        self, path: str, tile_type: str, tile_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Create a tile."""
        return self._post(f"{path}/@tiles/{tile_type}/{tile_id}", json=data)

    def update(
        self, path: str, tile_type: str, tile_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """Update a tile."""
        return self._put(f"{path}/@tiles/{tile_type}/{tile_id}", json=data)

    def delete(self, path: str, tile_type: str, tile_id: str) -> None:
        """Delete a tile."""
        self._delete(f"{path}/@tiles/{tile_type}/{tile_id}")
