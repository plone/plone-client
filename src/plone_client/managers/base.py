"""Base class of the managers."""

from typing import TYPE_CHECKING


if TYPE_CHECKING:
    from ..client import PloneClient


class BaseManager:
    """Group the calls to one area of ``plone.restapi``.

    A manager holds no state of its own: every call goes through the
    :class:`~plone_client.PloneClient` it belongs to.

    :param client: The client.
    """

    def __init__(self, client: "PloneClient") -> None:
        self._client = client

    def _resolve(self, ref: str) -> str:
        """Site path for a path, URL, ``uid:<UID>`` or ``resolveuid`` link.

        :param ref: The reference.
        :returns: The site path.
        """
        return self._client.content.resolve(ref)

    def _service(self, ref: str, service: str) -> str:
        """Path of a service on an item.

        :param ref: Path, URL or UID reference of the item.
        :param service: Service name with its arguments (``@workflow/publish``).
        :returns: Site path of the service.
        """
        return f"{self._resolve(ref).rstrip('/')}/{service}"
