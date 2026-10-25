"""
Working copy manager — ``@workingcopy`` endpoint.

Requires ``plone.app.iterate`` to be installed on the Plone site.
"""

from __future__ import annotations

from .base import BaseManager
from typing import Any


class WorkingCopyManager(BaseManager):
    """
    Manage working copies (check-out / check-in) via ``@workingcopy``.

    >>> wc = client.working_copy.checkout("/news/my-article")
    >>> wc_path = wc["@id"].replace(client.config.base_url, "")
    >>> client.content.update(wc_path, title="Updated Title")
    >>> client.working_copy.checkin(wc_path, message="Fixed typo")
    """

    def checkout(self, path: str) -> dict[str, Any]:
        """
        Check out a working copy of *path*.

        Returns the new working copy object representation.
        """
        return self._post(f"{path}/@workingcopy")

    def checkin(self, path: str, message: str = "") -> dict[str, Any]:
        """
        Check in the working copy at *path*, merging changes back to baseline.

        :param path: Path of the working copy (not the baseline).
        :type path: str
        :param message: Optional check-in comment.
        :type message: str
        """
        return self._patch(f"{path}/@workingcopy", json={"checkin_message": message})

    def cancel(self, path: str) -> None:
        """
        Cancel the checkout — discards the working copy at *path*.
        """
        self._delete(f"{path}/@workingcopy")

    def info(self, path: str) -> dict[str, Any]:
        """
        Get working copy status for *path*.

        Returns info about whether *path* is a baseline or a working copy,
        and links to the counterpart.
        """
        return self._get(f"{path}/@workingcopy")
