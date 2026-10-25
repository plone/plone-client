"""
examples/user_management.py
============================
Demonstrates user and group management, plus local role (sharing) assignment.

Run:
    python examples/user_management.py
"""

from __future__ import annotations

from plone_client import PloneClient
from plone_client import PloneConflictError
from plone_client import PloneNotFoundError


def main() -> None:
    with PloneClient() as client:
        # ── Create a user ─────────────────────────────────────────────
        try:
            user = client.users.create(
                username="jane",
                email="jane@example.com",
                password="Secret1234!",
                roles=["Member"],
                fullname="Jane Doe",
            )
            print(f"Created user: {user.get('id', 'jane')}")
        except PloneConflictError:
            print("User 'jane' already exists")

        # ── Update user profile ───────────────────────────────────────
        client.users.update("jane", fullname="Jane A. Doe")
        print("Updated fullname")

        # ── Create a group ────────────────────────────────────────────
        try:
            group = client.groups.create(
                groupname="editors",
                title="Content Editors",
                description="Users allowed to edit content",
                roles=["Contributor", "Editor"],
            )
            print(f"Created group: {group.get('id', 'editors')}")
        except PloneConflictError:
            print("Group 'editors' already exists")

        # ── Add user to group ─────────────────────────────────────────
        client.groups.add_member("editors", "jane")
        print("Added jane to editors")

        # ── Grant local roles on a piece of content ───────────────────
        try:
            client.sharing.update(
                "/news",
                entries=[
                    {
                        "id": "jane",
                        "type": "user",
                        "roles": {"Contributor": True, "Editor": True},
                    },
                    {
                        "id": "editors",
                        "type": "group",
                        "roles": {"Reviewer": True},
                    },
                ],
                inherit=True,
            )
            print("Sharing updated on /news")
        except PloneNotFoundError:
            print("/news does not exist — skipping sharing")

        # ── Read current sharing settings ────────────────────────────
        try:
            sharing = client.sharing.get("/news")
            print(f"Sharing entries on /news: {len(sharing.get('entries', []))}")
        except PloneNotFoundError:
            pass

        # ── Search principals (users + groups combined) ───────────────
        principals = client.utilities.search_principals("jane")
        found_users = principals.get("users", [])
        print(f"Principal search 'jane': {len(found_users)} users found")

        # ── Current user info ─────────────────────────────────────────
        me = client.users.my_information()
        print(f"Currently logged in as: {me.get('id', '?')}")

        # ── Clean up ─────────────────────────────────────────────────
        try:
            client.groups.remove_member("editors", "jane")
            client.groups.delete("editors")
            client.users.delete("jane")
            print("Cleaned up user and group")
        except PloneNotFoundError:
            pass


if __name__ == "__main__":
    main()
