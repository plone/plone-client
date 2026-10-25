"""
Users & groups manager.

Covers:
- ``@users``
- ``@groups``
- ``@roles``
- ``@sharing`` (local roles)
- ``@user-information``
- ``@my-information`` (current user)
"""

from __future__ import annotations

from .base import BaseManager
from typing import Any


class UsersManager(BaseManager):
    """Manage Plone users."""

    def list(
        self, query: str = "", groups_filter: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        List users.

        :param query: Filter by username / fullname substring.
        :type query: str
        :param groups_filter: Only return members of these group ids.
        :type groups_filter: list[str] or None
        """
        params: dict[str, Any] = {}
        if query:
            params["query"] = query
        if groups_filter:
            params["groups-filter:list"] = groups_filter
        return self._get("/@users", params=params or None)

    def get(self, user_id: str) -> dict[str, Any]:
        """Fetch a single user by id."""
        return self._get(f"/@users/{user_id}")

    def create(
        self,
        username: str,
        email: str,
        password: str | None = None,
        roles: list[str] | None = None,
        **fields: Any,
    ) -> dict[str, Any]:
        """Create a new user."""
        payload: dict[str, Any] = {
            "username": username,
            "email": email,
            **fields,
        }
        if password:
            payload["password"] = password
        if roles:
            payload["roles"] = roles
        return self._post("/@users", json=payload)

    def update(self, user_id: str, **fields: Any) -> dict[str, Any]:
        """Update user *user_id*."""
        return self._patch(f"/@users/{user_id}", json=fields)

    def delete(self, user_id: str) -> None:
        """Delete user *user_id*."""
        self._delete(f"/@users/{user_id}")

    def reset_password(self, user_id: str) -> dict[str, Any]:
        """Trigger a password reset e-mail for *user_id*."""
        return self._post(f"/@users/{user_id}/reset-password")

    def my_information(self) -> dict[str, Any]:
        """Return information about the currently logged-in user."""
        return self._get("/@my-information")

    def update_my_information(self, **fields: Any) -> dict[str, Any]:
        """Update current user's profile."""
        return self._patch("/@my-information", json=fields)


class GroupsManager(BaseManager):
    """Manage Plone groups."""

    def list(self, query: str = "") -> list[dict[str, Any]]:
        """List groups, optionally filtered by *query*."""
        params = {"query": query} if query else None
        return self._get("/@groups", params=params)

    def get(self, group_id: str) -> dict[str, Any]:
        """Fetch group *group_id*."""
        return self._get(f"/@groups/{group_id}")

    def create(
        self,
        groupname: str,
        title: str = "",
        description: str = "",
        roles: list[str] | None = None,
        groups: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new group."""
        payload: dict[str, Any] = {"groupname": groupname}
        if title:
            payload["title"] = title
        if description:
            payload["description"] = description
        if roles:
            payload["roles"] = roles
        if groups:
            payload["groups"] = groups
        return self._post("/@groups", json=payload)

    def update(self, group_id: str, **fields: Any) -> dict[str, Any]:
        """Update group *group_id*."""
        return self._patch(f"/@groups/{group_id}", json=fields)

    def delete(self, group_id: str) -> None:
        """Delete group *group_id*."""
        self._delete(f"/@groups/{group_id}")

    def add_member(self, group_id: str, user_id: str) -> dict[str, Any]:
        """Add *user_id* to *group_id*."""
        return self._post(f"/@groups/{group_id}/members/{user_id}")

    def remove_member(self, group_id: str, user_id: str) -> None:
        """Remove *user_id* from *group_id*."""
        self._delete(f"/@groups/{group_id}/members/{user_id}")


class SharingManager(BaseManager):
    """Manage local roles (content-level sharing)."""

    def get(self, path: str) -> dict[str, Any]:
        """Get sharing / local roles for *path*."""
        return self._get(f"{path}/@sharing")

    def update(
        self,
        path: str,
        entries: list[dict[str, Any]],
        inherit: bool | None = None,
    ) -> dict[str, Any]:
        """
        Update local roles on *path*.

        :param entries: List of sharing entries, e.g.::

                [{"id": "john", "type": "user", "roles": {"Contributor": True}}]
        :type entries: list[dict]
        :param inherit: Whether to inherit roles from parent objects.
        :type inherit: bool or None
        """
        payload: dict[str, Any] = {"entries": entries}
        if inherit is not None:
            payload["inherit"] = inherit
        return self._post(f"{path}/@sharing", json=payload)

    def search_principals(self, path: str, query: str) -> dict[str, Any]:
        """Search for users/groups to share *path* with."""
        return self._get(f"{path}/@sharing", params={"search": query})
