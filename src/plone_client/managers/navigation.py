"""Navigation, breadcrumbs, actions and other contextual information."""

from .base import BaseManager
from collections.abc import Iterable
from typing import Any


class NavigationManager(BaseManager):
    """Contextual information about an item."""

    def navigation(self, ref: str = "/", *, depth: int | None = None) -> dict[str, Any]:
        """Top navigation (``@navigation``).

        :param ref: Path or URL of the context.
        :param depth: Levels of the navigation tree to include.
        :returns: ``items`` of the navigation.
        """
        return self._client.get(
            self._service(ref, "@navigation"), **{"expand.navigation.depth": depth}
        )

    def breadcrumbs(self, ref: str) -> dict[str, Any]:
        """Breadcrumbs of an item (``@breadcrumbs``).

        :param ref: Path or URL of the item.
        :returns: ``items`` from the navigation root to the item.
        """
        return self._client.get(self._service(ref, "@breadcrumbs"))

    def contextnavigation(self, ref: str, **params: Any) -> dict[str, Any]:
        """Navigation portlet of an item (``@contextnavigation``).

        :param ref: Path or URL of the item.
        :param params: Portlet options, such as
            ``expand.contextnavigation.bottomLevel``.
        :returns: The navigation tree.
        """
        return self._client.get(self._service(ref, "@contextnavigation"), **params)

    def navroot(self, ref: str = "/") -> dict[str, Any]:
        """Navigation root of an item (``@navroot``).

        On a multilingual site, this is the language root folder.

        :param ref: Path or URL of the item.
        :returns: ``navroot``, the serialized root.
        """
        return self._client.get(self._service(ref, "@navroot"))

    def actions(
        self, ref: str = "/", *, categories: Iterable[str] | None = None
    ) -> dict[str, Any]:
        """CMF actions available on an item (``@actions``).

        :param ref: Path or URL of the item.
        :param categories: Only these categories (``object``, ``user``…).
        :returns: Actions by category.
        """
        params = {"categories:list": list(categories)} if categories else {}
        return self._client.get(self._service(ref, "@actions"), **params)

    def inherit(self, ref: str, behaviors: str | Iterable[str]) -> dict[str, Any]:
        """Field values an item inherits from its parents (``@inherit``).

        :param ref: Path or URL of the item.
        :param behaviors: Behaviors to look up, such as ``plone.navigationroot``.
        :returns: For each behavior, the closest item that has it and its data.
        """
        if not isinstance(behaviors, str):
            behaviors = ",".join(behaviors)
        return self._client.get(
            self._service(ref, "@inherit"), **{"expand.inherit.behaviors": behaviors}
        )
