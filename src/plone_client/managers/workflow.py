"""Workflow, versions and working copies of items."""

from .base import BaseManager
from typing import Any


class WorkflowManager(BaseManager):
    """Workflow state and transitions (``@workflow``)."""

    def info(self, ref: str) -> dict[str, Any]:
        """Current state, history and available transitions of an item.

        :param ref: Path or URL of the item.
        :returns: ``state``, ``history`` and ``transitions``.
        """
        return self._client.get(self._service(ref, "@workflow"))

    def transition(
        self,
        ref: str,
        transition: str,
        *,
        comment: str | None = None,
        effective: str | None = None,
        expires: str | None = None,
        include_children: bool = False,
    ) -> dict[str, Any]:
        """Run a workflow transition.

        :param ref: Path or URL of the item.
        :param transition: Transition id, such as ``publish`` or ``retract``.
        :param comment: Comment stored in the workflow history.
        :param effective: Publication date (ISO 8601).
        :param expires: Expiration date (ISO 8601).
        :param include_children: Also run it on the items inside a folder.
        :returns: The new history entry, with ``review_state``.
        :raises PloneBadRequestError: If the transition is not available.
        """
        data: dict[str, Any] = {}
        if comment is not None:
            data["comment"] = comment
        if effective is not None:
            data["effective"] = effective
        if expires is not None:
            data["expires"] = expires
        if include_children:
            data["include_children"] = True
        return self._client.post(
            self._service(ref, f"@workflow/{transition}"), data or None
        )


class HistoryManager(BaseManager):
    """Versions and workflow history of an item (``@history``)."""

    def list(self, ref: str) -> list[dict[str, Any]]:
        """History entries of an item, newest first.

        :param ref: Path or URL of the item.
        :returns: Versioning and workflow entries.
        """
        return self._client.get(self._service(ref, "@history"))

    def get(self, ref: str, version: int) -> dict[str, Any]:
        """An older version of an item.

        :param ref: Path or URL of the item.
        :param version: Version number, from :meth:`list`.
        :returns: The item as it was.
        """
        return self._client.get(self._service(ref, f"@history/{version}"))

    def revert(self, ref: str, version: int) -> dict[str, Any]:
        """Revert an item to an older version.

        :param ref: Path or URL of the item.
        :param version: Version number, from :meth:`list`.
        :returns: A confirmation message.
        """
        return self._client.patch(self._service(ref, "@history"), {"version": version})


class WorkingCopyManager(BaseManager):
    """Working copies of published items (``@workingcopy``).

    Needs ``plone.app.iterate`` installed on the site.
    """

    def info(self, ref: str) -> dict[str, Any]:
        """Working copy of an item, or the baseline of a working copy.

        :param ref: Path or URL of the baseline or of the working copy.
        :returns: ``working_copy`` and ``working_copy_of``.
        """
        return self._client.get(self._service(ref, "@workingcopy"))

    def create(self, ref: str) -> dict[str, Any]:
        """Check out an item into a working copy.

        :param ref: Path or URL of the item.
        :returns: ``@id`` of the working copy.
        """
        return self._client.post(self._service(ref, "@workingcopy"))

    def check_in(self, ref: str) -> None:
        """Apply a working copy to its baseline and remove it.

        :param ref: Path or URL of the working copy or of the baseline.
        """
        self._client.patch(self._service(ref, "@workingcopy"))

    def cancel(self, ref: str) -> None:
        """Remove a working copy without applying it.

        :param ref: Path or URL of the working copy or of the baseline.
        """
        self._client.delete(self._service(ref, "@workingcopy"))
