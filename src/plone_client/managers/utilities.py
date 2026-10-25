"""
Miscellaneous plone.restapi endpoints that don't belong to a larger domain.

Covers:
- ``@resolveuid``        — resolve a UID to its URL / object
- ``@ids``               — list child object ids in a container
- ``@principals``        — unified user+group search
- ``@userschema``        — user registration field schema
- ``@expandable-fields`` — list fields that can be expanded inline
- ``@navigation-root``   — navigation root info for a given path
- ``@clipboard``         — clipboard state
- ``@paste``             — paste clipboard contents
- ``@content-rules``     — content rules management
- ``@config``            — Volto / site configuration
- ``@components``        — Volto component registry
- ``@sidebar``           — Volto sidebar data
"""

from __future__ import annotations

from .base import BaseManager
from typing import Any


class UtilitiesManager(BaseManager):
    """Miscellaneous plone.restapi utilities."""

    # ------------------------------------------------------------------
    # UID resolution
    # ------------------------------------------------------------------

    def resolve_uid(self, uid: str) -> dict[str, Any]:
        """
        Resolve a content UID to its URL and basic metadata.

        :param uid: The 32-character Plone UID string.
        :type uid: str
        :returns: Object representation including ``@id`` (canonical URL).
        :rtype: dict
        """
        return self._get(f"/@resolveuid/{uid}")

    # ------------------------------------------------------------------
    # Child IDs
    # ------------------------------------------------------------------

    def ids(self, path: str) -> list[str]:
        """
        Return a list of child object ids inside a container at *path*.

        This is a lightweight alternative to fetching full object
        representations when you only need the identifiers.
        """
        result = self._get(f"{path}/@ids")
        # API returns either a plain list or {"items": [...]}
        if isinstance(result, list):
            return result
        return result.get("items", [])

    # ------------------------------------------------------------------
    # Principals (unified user + group search)
    # ------------------------------------------------------------------

    def search_principals(
        self,
        query: str,
        *,
        path: str = "/",
        groups_only: bool = False,
        users_only: bool = False,
    ) -> dict[str, Any]:
        """
        Search users and groups simultaneously via ``@principals``.

        :param query: Search string matched against name / title.
        :type query: str
        :param path: Scope context for local role resolution (defaults to site root).
        :type path: str
        :param groups_only: Return only groups.
        :type groups_only: bool
        :param users_only: Return only users.
        :type users_only: bool
        """
        params: dict[str, Any] = {"search": query}
        if groups_only:
            params["type"] = "group"
        elif users_only:
            params["type"] = "user"
        return self._get(f"{path}/@principals", params=params)

    # ------------------------------------------------------------------
    # User registration schema
    # ------------------------------------------------------------------

    def user_schema(self) -> dict[str, Any]:
        """Return the JSON Schema for user self-registration (``@userschema``)."""
        return self._get("/@userschema")

    # ------------------------------------------------------------------
    # Expandable fields
    # ------------------------------------------------------------------

    def expandable_fields(self, path: str) -> list[str]:
        """
        List fields that can be expanded inline for a content object at *path*.

        Expandable fields are requested via ``?expand=fieldname`` on GET.
        """
        result = self._get(f"{path}/@expandable-fields")
        if isinstance(result, list):
            return result
        return result.get("items", [])

    # ------------------------------------------------------------------
    # Navigation root
    # ------------------------------------------------------------------

    def navigation_root(self, path: str = "/") -> dict[str, Any]:
        """
        Return navigation root information for *path*.

        In a multi-site Plone setup the navigation root may differ from
        the Plone site root.
        """
        return self._get(f"{path}/@navigation-root")

    # ------------------------------------------------------------------
    # Clipboard / paste
    # ------------------------------------------------------------------

    def clipboard(self, path: str) -> dict[str, Any]:
        """Return the current clipboard state for the user at *path*."""
        return self._get(f"{path}/@clipboard")

    def copy_to_clipboard(self, path: str, uids: list[str]) -> dict[str, Any]:
        """Copy objects identified by *uids* into the clipboard."""
        return self._post(f"{path}/@clipboard", json={"uids": uids, "op": "copy"})

    def cut_to_clipboard(self, path: str, uids: list[str]) -> dict[str, Any]:
        """Cut objects identified by *uids* into the clipboard."""
        return self._post(f"{path}/@clipboard", json={"uids": uids, "op": "cut"})

    def paste(self, path: str) -> dict[str, Any]:
        """Paste clipboard contents into *path*."""
        return self._post(f"{path}/@paste")

    # ------------------------------------------------------------------
    # Content rules
    # ------------------------------------------------------------------

    def content_rules(self, path: str = "/") -> dict[str, Any]:
        """List content rules available at *path*."""
        return self._get(f"{path}/@content-rules")

    def get_content_rule(self, path: str, rule_id: str) -> dict[str, Any]:
        """Fetch content rule *rule_id* at *path*."""
        return self._get(f"{path}/@content-rules/{rule_id}")

    def apply_content_rule(self, path: str, rule_id: str) -> dict[str, Any]:
        """Apply content rule *rule_id* to *path*."""
        return self._post(f"{path}/@content-rules/{rule_id}")

    # ------------------------------------------------------------------
    # Volto / site config
    # ------------------------------------------------------------------

    def site_config(self) -> dict[str, Any]:
        """
        Return Volto/site configuration via ``@config``.

        Includes blocks config, allowed blocks, image scales, etc.
        """
        return self._get("/@config")

    def update_site_config(self, **settings: Any) -> dict[str, Any]:
        """Update site configuration settings."""
        return self._patch("/@config", json=settings)

    # ------------------------------------------------------------------
    # Volto component registry
    # ------------------------------------------------------------------

    def components(self, path: str = "/") -> dict[str, Any]:
        """Return the Volto component registry for *path* (``@components``)."""
        return self._get(f"{path}/@components")

    # ------------------------------------------------------------------
    # Volto sidebar
    # ------------------------------------------------------------------

    def sidebar(self, path: str) -> dict[str, Any]:
        """Return sidebar data for *path* (``@sidebar``)."""
        return self._get(f"{path}/@sidebar")
