"""Base class for all resource managers."""

from __future__ import annotations

from ..connection import PloneConnection
from typing import Any


class BaseManager:
    """
    All resource managers extend this class.

    :param connection: The shared :class:`~plone_client.connection.PloneConnection`.
    :type connection: PloneConnection
    """

    def __init__(self, connection: PloneConnection) -> None:
        self._conn = connection

    def _get(self, path: str, **kwargs: Any) -> Any:
        return self._conn.get(path, **kwargs).json()

    def _post(self, path: str, **kwargs: Any) -> Any:
        return self._conn.post(path, **kwargs).json()

    def _patch(self, path: str, **kwargs: Any) -> Any:
        return self._conn.patch(path, **kwargs).json()

    def _put(self, path: str, **kwargs: Any) -> Any:
        return self._conn.put(path, **kwargs).json()

    def _delete(self, path: str, **kwargs: Any) -> None:
        self._conn.delete(path, **kwargs)
