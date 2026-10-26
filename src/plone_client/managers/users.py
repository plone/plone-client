"""Users, groups, roles and sharing."""

from .base import BaseManager
from collections.abc import Iterable
from collections.abc import Mapping
from typing import Any


class UsersManager(BaseManager):
    """Site users (``@users``)."""

    def list(
        self,
        *,
        query: str | None = None,
        search: str | None = None,
        groups: Iterable[str] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Users of the site.

        :param query: Text the user id must contain.
        :param search: Text to look for in the id, full name and email.
        :param groups: Only members of these groups.
        :param limit: Maximum number of users (the site defaults to 25).
        :returns: The users.
        """
        return self._client.get(
            "/@users",
            query=query,
            search=search,
            limit=limit,
            **{"groups-filter:list": list(groups) if groups else None},
        )

    def get(self, user_id: str) -> dict[str, Any]:
        """A user.

        :param user_id: Id of the user.
        :returns: The user, with roles and groups.
        """
        return self._client.get(f"/@users/{user_id}")

    def create(
        self, username: str, data: Mapping[str, Any] | None = None, **fields: Any
    ) -> dict[str, Any]:
        """Create a user.

        :param username: Login name.
        :param data: Other fields: ``email``, ``fullname``, ``password``,
            ``roles``, ``groups``, ``sendPasswordReset``…
        :param fields: More fields, merged over ``data``.
        :returns: The new user.
        """
        return self._client.post(
            "/@users", {"username": username, **(data or {}), **fields}
        )

    def update(
        self, user_id: str, data: Mapping[str, Any] | None = None, **fields: Any
    ) -> None:
        """Change a user.

        :param user_id: Id of the user.
        :param data: Fields to change; ``roles`` maps role names to
            ``True``/``False``.
        :param fields: More fields, merged over ``data``.
        """
        self._client.patch(f"/@users/{user_id}", {**(data or {}), **fields})

    def delete(
        self,
        user_id: str,
        *,
        delete_memberareas: bool = True,
        delete_localroles: bool = True,
    ) -> None:
        """Delete a user.

        :param user_id: Id of the user.
        :param delete_memberareas: Also delete the user's member folder.
        :param delete_localroles: Also remove the user's local roles.
        """
        self._client.request(
            "DELETE",
            f"/@users/{user_id}",
            params={
                "delete_memberareas": int(delete_memberareas),
                "delete_localroles": int(delete_localroles),
            },
        )

    def reset_password(self, user_id: str) -> None:
        """Send the user an email to reset the password.

        :param user_id: Id of the user.
        """
        self._client.post(f"/@users/{user_id}/reset-password")

    def update_password(
        self, user_id: str, new_password: str, *, old_password: str | None = None
    ) -> None:
        """Set a new password.

        Managers set any user's password without the old one; users change
        their own by giving it.

        :param user_id: Id of the user.
        :param new_password: The new password.
        :param old_password: The current password.
        """
        data = {"new_password": new_password}
        if old_password is not None:
            data["old_password"] = old_password
        self._client.post(f"/@users/{user_id}/reset-password", data)

    def schema(self, *, registration: bool = False) -> dict[str, Any]:
        """JSON schema of the user fields (``@userschema``).

        :param registration: Schema of the registration form instead.
        :returns: The schema.
        """
        return self._client.get(
            "/@userschema/registration" if registration else "/@userschema"
        )

    def portrait(self, user_id: str | None = None) -> bytes:
        """Portrait image of a user (``@portrait``).

        :param user_id: Id of the user; the current user when missing.
        :returns: The image.
        """
        path = f"/@portrait/{user_id}" if user_id else "/@portrait"
        return self._client.request("GET", path).content


class GroupsManager(BaseManager):
    """Site groups (``@groups``)."""

    def list(
        self, *, query: str | None = None, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Groups of the site.

        :param query: Text the group id must contain.
        :param limit: Maximum number of groups.
        :returns: The groups.
        """
        return self._client.get("/@groups", query=query, limit=limit)

    def get(self, group_id: str) -> dict[str, Any]:
        """A group, with its members.

        :param group_id: Id of the group.
        :returns: The group.
        """
        return self._client.get(f"/@groups/{group_id}")

    def create(
        self, groupname: str, data: Mapping[str, Any] | None = None, **fields: Any
    ) -> dict[str, Any]:
        """Create a group.

        :param groupname: Id of the group.
        :param data: Other fields: ``title``, ``description``, ``email``,
            ``roles``, ``groups``, ``users``.
        :param fields: More fields, merged over ``data``.
        :returns: The new group.
        """
        return self._client.post(
            "/@groups", {"groupname": groupname, **(data or {}), **fields}
        )

    def update(
        self, group_id: str, data: Mapping[str, Any] | None = None, **fields: Any
    ) -> None:
        """Change a group.

        :param group_id: Id of the group.
        :param data: Fields to change; ``users`` maps user ids to
            ``True`` (add) or ``False`` (remove).
        :param fields: More fields, merged over ``data``.
        """
        self._client.patch(f"/@groups/{group_id}", {**(data or {}), **fields})

    def delete(self, group_id: str) -> None:
        """Delete a group.

        :param group_id: Id of the group.
        """
        self._client.delete(f"/@groups/{group_id}")

    def add_members(self, group_id: str, user_ids: str | Iterable[str]) -> None:
        """Add users to a group.

        :param group_id: Id of the group.
        :param user_ids: Id of a user, or several.
        """
        ids = [user_ids] if isinstance(user_ids, str) else user_ids
        self.update(group_id, users=dict.fromkeys(ids, True))

    def remove_members(self, group_id: str, user_ids: str | Iterable[str]) -> None:
        """Remove users from a group.

        :param group_id: Id of the group.
        :param user_ids: Id of a user, or several.
        """
        ids = [user_ids] if isinstance(user_ids, str) else user_ids
        self.update(group_id, users=dict.fromkeys(ids, False))


class SharingManager(BaseManager):
    """Local roles (``@sharing``), principals and roles."""

    def get(
        self, ref: str, *, search: str | None = None, include_titles: bool = False
    ) -> dict[str, Any]:
        """Local roles of an item.

        :param ref: Path or URL of the item.
        :param search: Also list users and groups matching this text.
        :param include_titles: Add role titles to the answer.
        :returns: ``entries``, ``inherit`` and ``available_roles``.
        """
        return self._client.get(
            self._service(ref, "@sharing"),
            search=search,
            include_titles=1 if include_titles else None,
        )

    def update(
        self,
        ref: str,
        entries: Iterable[Mapping[str, Any]],
        *,
        inherit: bool | None = None,
    ) -> None:
        """Change local roles of an item.

        :param ref: Path or URL of the item.
        :param entries: Entries with ``id``, ``type`` (``user`` or ``group``)
            and ``roles``, a mapping of role names to ``True``/``False``.
        :param inherit: Inherit local roles from the parent.
        """
        data: dict[str, Any] = {"entries": [dict(entry) for entry in entries]}
        if inherit is not None:
            data["inherit"] = inherit
        self._client.post(self._service(ref, "@sharing"), data)

    def principals(self, search: str) -> dict[str, Any]:
        """Users and groups matching a text (``@principals``).

        :param search: Text to look for.
        :returns: ``users`` and ``groups``.
        """
        return self._client.get("/@principals", search=search)

    def roles(self) -> list[dict[str, Any]]:
        """Roles defined on the site (``@roles``).

        :returns: The roles, with ``id`` and ``title``.
        """
        return self._client.get("/@roles")
