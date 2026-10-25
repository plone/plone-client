"""
System-level managers:
- Registry
- Controlpanels
- Addons
- Site info
- Transactions
- Vocabularies
- Types (content type definitions)
"""

from __future__ import annotations

from .base import BaseManager
from typing import Any


class RegistryManager(BaseManager):
    """Read and write entries in the Plone configuration registry."""

    def get(self, key: str | None = None) -> dict[str, Any]:
        """
        Get registry entries.

        :param key: Full dotted registry key.  Returns all entries when *None*.
        :type key: str or None
        """
        path = f"/@registry/{key}" if key else "/@registry"
        return self._get(path)

    def set(self, key: str, value: Any) -> None:
        """Update registry entry *key*."""
        self._patch(f"/@registry/{key}", json={"value": value})


class ControlpanelsManager(BaseManager):
    """Interact with Plone control panels."""

    def list(self) -> dict[str, Any]:
        """List available control panels."""
        return self._get("/@controlpanels")

    def get(self, panel_id: str) -> dict[str, Any]:
        """Fetch the schema and current data of control panel *panel_id*."""
        return self._get(f"/@controlpanels/{panel_id}")

    def update(self, panel_id: str, **fields: Any) -> dict[str, Any]:
        """Update settings in control panel *panel_id*."""
        return self._patch(f"/@controlpanels/{panel_id}", json=fields)


class AddonsManager(BaseManager):
    """Manage Plone add-ons."""

    def list(self) -> dict[str, Any]:
        """List all available add-ons and their install status."""
        return self._get("/@addons")

    def get(self, addon_id: str) -> dict[str, Any]:
        """Get info about a specific add-on."""
        return self._get(f"/@addons/{addon_id}")

    def install(self, addon_id: str) -> dict[str, Any]:
        """Install add-on *addon_id*."""
        return self._post(f"/@addons/{addon_id}/install")

    def uninstall(self, addon_id: str) -> dict[str, Any]:
        """Uninstall add-on *addon_id*."""
        return self._post(f"/@addons/{addon_id}/uninstall")


class SiteManager(BaseManager):
    """Top-level site information."""

    def info(self) -> dict[str, Any]:
        """Return basic site information (``GET /``)."""
        return self._get("/")

    def types(self) -> dict[str, Any]:
        """List all available content types (``GET /@types``)."""
        return self._get("/@types")

    def type_schema(self, type_id: str) -> dict[str, Any]:
        """Return the JSON Schema for content type *type_id*."""
        return self._get(f"/@types/{type_id}")

    def vocabularies(self) -> dict[str, Any]:
        """List available vocabularies."""
        return self._get("/@vocabularies")

    def vocabulary(self, vocab_id: str, query: str = "") -> dict[str, Any]:
        """
        Fetch items from vocabulary *vocab_id*.

        :param vocab_id: Vocabulary identifier.
        :type vocab_id: str
        :param query: Optional filter string.
        :type query: str
        """
        params = {"query": query} if query else None
        return self._get(f"/@vocabularies/{vocab_id}", params=params)

    def roles(self) -> list[str]:
        """List all roles defined in the site."""
        return self._get("/@roles")

    def email_notification(
        self,
        name: str,
        email: str,
        subject: str,
        message: str,
    ) -> dict[str, Any]:
        """Send a contact e-mail via ``@email-notification``."""
        return self._post(
            "/@email-notification",
            json={"name": name, "from": email, "subject": subject, "message": message},
        )

    def email_send(
        self,
        recipients: list[str],
        subject: str,
        message: str,
    ) -> dict[str, Any]:
        """Send an e-mail via ``@email-send`` (requires Manager role)."""
        return self._post(
            "/@email-send",
            json={"recipients": recipients, "subject": subject, "message": message},
        )

    def upgrade(self) -> dict[str, Any]:
        """Trigger a site upgrade check/run (``@upgrade``)."""
        return self._post("/@upgrade")

    def transactions(
        self,
        size: int = 20,
    ) -> dict[str, Any]:
        """List recent ZODB transactions (``@transactions``)."""
        return self._get("/@transactions", params={"size": size})

    def undo(self, transaction_id: str) -> dict[str, Any]:
        """Undo a transaction by id."""
        return self._patch("/@transactions", json={"transaction_id": transaction_id})
