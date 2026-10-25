"""
Content manager — create, read, update, delete, copy, move Plone content.

Covers the core content operations from plone.restapi:
- Content CRUD (GET / POST / PATCH / DELETE)
- Navigation
- Breadcrumbs
- Contextual navigation
- Workflow transitions
- Locking
- Aliases
- Ordering (folder contents)
"""

from __future__ import annotations

from .base import BaseManager
from typing import Any


class ContentManager(BaseManager):
    """Manage Plone content objects."""

    # ------------------------------------------------------------------
    # Basic CRUD
    # ------------------------------------------------------------------

    def get(self, path: str, **params: Any) -> dict[str, Any]:
        """
        Fetch a content object.

        :param path: Site-relative path, e.g. ``"/news/my-article"``.
        :type path: str
        :param params: Extra query-string parameters forwarded to the API
            (e.g. ``fullobjects=True``).
        """
        return self._get(path, params=params or None)

    def create(
        self,
        container_path: str,
        type_: str,
        title: str,
        **fields: Any,
    ) -> dict[str, Any]:
        """
        Create a new content object inside *container_path*.

        :param container_path: Path of the parent container.
        :type container_path: str
        :param type_: Plone content type id, e.g. ``"Document"``.
        :type type_: str
        :param title: Object title (also used to generate the id if not given).
        :type title: str
        :param fields: Additional field values to set on creation.
        """
        payload = {"@type": type_, "title": title, **fields}
        return self._post(container_path, json=payload)

    def update(self, path: str, **fields: Any) -> dict[str, Any]:
        """
        Partially update a content object (PATCH semantics).

        :param path: Path to the content object.
        :type path: str
        :param fields: Field/value pairs to update.
        """
        return self._patch(path, json=fields)

    def replace(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """
        Fully replace a content object (PUT semantics).

        :param path: Path to the content object.
        :type path: str
        :param payload: Full serialised representation of the object.
        :type payload: dict
        """
        return self._put(path, json=payload)

    def delete(self, path: str) -> None:
        """Delete a content object."""
        self._delete(path)

    # ------------------------------------------------------------------
    # Copy & Move
    # ------------------------------------------------------------------

    def copy(self, source: str, target: str) -> dict[str, Any]:
        """
        Copy *source* into *target* container.

        Uses ``POST /@copy`` on the source.
        """
        return self._post(f"{source}/@copy", json={"target": target})

    def move(self, source: str, target: str) -> dict[str, Any]:
        """
        Move *source* into *target* container.

        Uses ``POST /@move`` on the source.
        """
        return self._post(f"{source}/@move", json={"target": target})

    # ------------------------------------------------------------------
    # Navigation & breadcrumbs
    # ------------------------------------------------------------------

    def navigation(self, path: str = "/", depth: int = 1) -> dict[str, Any]:
        """Fetch the navigation tree rooted at *path*."""
        return self._get(f"{path}/@navigation", params={"depth": depth})

    def breadcrumbs(self, path: str) -> dict[str, Any]:
        """Fetch breadcrumbs for *path*."""
        return self._get(f"{path}/@breadcrumbs")

    def contextnavigation(self, path: str) -> dict[str, Any]:
        """Fetch contextual navigation for *path*."""
        return self._get(f"{path}/@contextnavigation")

    # ------------------------------------------------------------------
    # Workflow
    # ------------------------------------------------------------------

    def workflow(self, path: str) -> dict[str, Any]:
        """Get available workflow transitions for *path*."""
        return self._get(f"{path}/@workflow")

    def transition(
        self,
        path: str,
        transition_id: str,
        comment: str = "",
        effective: str | None = None,
        expires: str | None = None,
        include_children: bool = False,
    ) -> dict[str, Any]:
        """
        Execute a workflow transition.

        :param path: Content path.
        :type path: str
        :param transition_id: Transition id, e.g. ``"publish"``.
        :type transition_id: str
        :param comment: Optional reviewer comment.
        :type comment: str
        :param effective: ISO-8601 effective date string.
        :type effective: str or None
        :param expires: ISO-8601 expiration date string.
        :type expires: str or None
        :param include_children: Apply recursively to all contained objects.
        :type include_children: bool
        """
        payload: dict[str, Any] = {"comment": comment}
        if effective:
            payload["effective"] = effective
        if expires:
            payload["expires"] = expires
        if include_children:
            payload["include_children"] = True
        return self._post(f"{path}/@workflow/{transition_id}", json=payload)

    # ------------------------------------------------------------------
    # Locking
    # ------------------------------------------------------------------

    def lock(self, path: str, stealable: bool = True) -> dict[str, Any]:
        """Lock *path* for editing."""
        return self._post(f"{path}/@lock", json={"stealable": stealable})

    def unlock(self, path: str) -> dict[str, Any]:
        """Unlock *path*."""
        return self._delete_json(f"{path}/@lock")  # type: ignore[return-value]

    def lock_info(self, path: str) -> dict[str, Any]:
        """Get current lock info for *path*."""
        return self._get(f"{path}/@lock")

    def _delete_json(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return self._conn.delete(path, **kwargs).json()

    # ------------------------------------------------------------------
    # Aliases
    # ------------------------------------------------------------------

    def get_aliases(self, path: str) -> dict[str, Any]:
        """List URL aliases for *path*."""
        return self._get(f"{path}/@aliases")

    def add_alias(self, path: str, alias: str) -> dict[str, Any]:
        """Add a URL alias to *path*."""
        return self._post(f"{path}/@aliases", json={"items": [{"path": alias}]})

    def remove_alias(self, path: str, alias: str) -> None:
        """Remove a URL alias from *path*."""
        self._delete(f"{path}/@aliases", json={"items": [{"path": alias}]})

    # ------------------------------------------------------------------
    # Ordering (folder contents)
    # ------------------------------------------------------------------

    def order(
        self,
        folder_path: str,
        obj_id: str,
        delta: str | int,
    ) -> None:
        """
        Re-order an item inside a folder.

        :param folder_path: Path to the containing folder.
        :type folder_path: str
        :param obj_id: ``id`` of the object to move.
        :type obj_id: str
        :param delta: ``"top"`` | ``"bottom"`` | integer delta.
        :type delta: str or int
        """
        self._patch(
            f"{folder_path}/@content",
            json={"id": obj_id, "delta": delta},
        )

    # ------------------------------------------------------------------
    # Tiles / blocks
    # ------------------------------------------------------------------

    def get_blocksfield_serialization(self, path: str) -> dict[str, Any]:
        """Return blocks field serialisation for *path*."""
        return self._get(f"{path}/@blocks")
