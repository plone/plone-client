"""
Main entry point for plone-client.

Example usage::

    from plone_client import PloneClient

    client = PloneClient(
        base_url="https://my.plone.site",
        username="admin",
        password="secret",
    )

    with client:
        doc = client.content.create("/", "Document", title="Hello World")
        results = client.search.search({"portal_type": "Document"})
"""

from __future__ import annotations

from .config import PloneClientConfig
from .connection import PloneConnection
from .logging_config import logger
from .logging_config import setup_logging
from .managers import AddonsManager
from .managers import BlocksManager
from .managers import CommentsManager
from .managers import ContentManager
from .managers import ControlpanelsManager
from .managers import DatabaseManager
from .managers import FilesManager
from .managers import GroupsManager
from .managers import HistoryManager
from .managers import RegistryManager
from .managers import RelationsManager
from .managers import SearchManager
from .managers import SharingManager
from .managers import SiteManager
from .managers import TilesManager
from .managers import UsersManager
from .managers import UtilitiesManager
from .managers import WorkingCopyManager
from requests import Response
from typing import Any


class PloneClient:
    """
    High-level client for interacting with a Plone site via plone.restapi.

    All configuration can be passed explicitly or via environment variables
    (see :class:`~plone_client.config.PloneClientConfig`).

    :param base_url: Root URL of the Plone site, e.g. ``"https://my.plone.site"``.
        Falls back to ``PLONE_CLIENT_BASE_URL`` env var.
    :type base_url: str
    :param username: Plone username.  Falls back to ``PLONE_CLIENT_USERNAME``.
    :type username: str
    :param password: Plone password.  Falls back to ``PLONE_CLIENT_PASSWORD``.
    :type password: str
    :param token: Pre-issued JWT bearer token.  Falls back to ``PLONE_CLIENT_TOKEN``.
    :type token: str
    :param config: Pass a fully-built :class:`~plone_client.config.PloneClientConfig`
        to override individual settings at construction time.
    :type config: PloneClientConfig or None
    :param config_kwargs: Any other keyword argument accepted by
        :class:`~plone_client.config.PloneClientConfig`.

    >>> client = PloneClient(
    ...     "https://my.plone.site", username="admin", password="secret"
    ... )
    >>> client.open()
    >>> page = client.content.get("/front-page")
    >>> client.close()

    Using as context manager (recommended)::

        with PloneClient(...) as client:
            page = client.content.get("/front-page")
    """

    def __init__(
        self,
        base_url: str = "",
        *,
        username: str = "",
        password: str = "",
        token: str = "",
        config: PloneClientConfig | None = None,
        **config_kwargs: Any,
    ) -> None:
        if config is not None:
            self._config = config
        else:
            self._config = PloneClientConfig(
                base_url=base_url or config_kwargs.pop("base_url", ""),
                username=username or config_kwargs.pop("username", ""),
                password=password or config_kwargs.pop("password", ""),
                token=token or config_kwargs.pop("token", ""),
                **config_kwargs,
            )

        # Apply log level from config
        setup_logging(level=self._config.log_level)

        self._conn: PloneConnection = PloneConnection(self._config)
        self._init_managers()

    # ------------------------------------------------------------------
    # Resource managers
    # ------------------------------------------------------------------

    def _init_managers(self) -> None:
        self.content = ContentManager(self._conn)
        self.search = SearchManager(self._conn)
        self.users = UsersManager(self._conn)
        self.groups = GroupsManager(self._conn)
        self.sharing = SharingManager(self._conn)
        self.registry = RegistryManager(self._conn)
        self.controlpanels = ControlpanelsManager(self._conn)
        self.addons = AddonsManager(self._conn)
        self.site = SiteManager(self._conn)
        self.comments = CommentsManager(self._conn)
        self.history = HistoryManager(self._conn)
        self.tiles = TilesManager(self._conn)
        self.files = FilesManager(self._conn)
        self.relations = RelationsManager(self._conn)
        self.working_copy = WorkingCopyManager(self._conn)
        self.blocks = BlocksManager(self._conn)
        self.database = DatabaseManager(self._conn)
        self.utilities = UtilitiesManager(self._conn)

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def open(self) -> None:
        """
        Open the client session.

        If credentials are configured (and no static token is set), this
        performs a JWT login against ``/@login``.
        """
        if not self._config.has_token and self._config.has_credentials:
            self._conn.login()
        logger.info("PloneClient opened for %s", self._config.base_url)

    def close(self) -> None:
        """Close the session and log out (if using JWT auth)."""
        if not self._config.has_token:
            self._conn.logout()
        self._conn._session.close()
        logger.info("PloneClient closed")

    def __enter__(self) -> PloneClient:
        self.open()
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Escape hatch — call any custom service or endpoint
    # ------------------------------------------------------------------

    def request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Response:
        """
        Execute a raw HTTP request against the Plone site.

        This is the **escape hatch** for calling custom services,
        add-on endpoints, or anything not yet covered by the built-in
        managers.

        :param method: HTTP verb: ``GET``, ``POST``, ``PATCH``, ``PUT``, ``DELETE``, …
        :type method: str
        :param path: Path relative to ``base_url``, e.g. ``"/@my-custom-service"``.
            Absolute URLs are also accepted.
        :type path: str
        :param kwargs: Forwarded verbatim to :mod:`requests` (``json``, ``params``,
            ``data``, ``headers``, ``files``, ``timeout``, …).
        :returns: Raw response object — caller is responsible for parsing.
        :rtype: requests.Response

        >>> response = client.request(
        ...     "GET", "/@my-custom-endpoint", params={"key": "val"}
        ... )
        >>> data = response.json()

        >>> # POST a custom service with a file upload
        >>> with open("image.png", "rb") as f:
        ...     r = client.request("POST", "/news/@@upload", files={"file": f})
        """
        return self._conn._request(method.upper(), path, **kwargs)

    def get(self, path: str, **kwargs: Any) -> Response:
        """Shorthand for ``client.request("GET", path, ...)``."""
        return self._conn.get(path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Response:
        """Shorthand for ``client.request("POST", path, ...)``."""
        return self._conn.post(path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> Response:
        """Shorthand for ``client.request("PATCH", path, ...)``."""
        return self._conn.patch(path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> Response:
        """Shorthand for ``client.request("PUT", path, ...)``."""
        return self._conn.put(path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Response:
        """Shorthand for ``client.request("DELETE", path, ...)``."""
        return self._conn.delete(path, **kwargs)

    # ------------------------------------------------------------------
    # Auth helpers (re-exposed for convenience)
    # ------------------------------------------------------------------

    def login(self) -> None:
        """Manually trigger JWT login."""
        self._conn.login()

    def logout(self) -> None:
        """Manually trigger JWT logout."""
        self._conn.logout()

    def renew_token(self) -> None:
        """Renew the current JWT token."""
        self._conn.renew_token()

    @property
    def token(self) -> str:
        """The current bearer token."""
        return self._conn.token

    @property
    def config(self) -> PloneClientConfig:
        """The active configuration."""
        return self._config

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:  # pragma: no cover
        return f"PloneClient(base_url={self._config.base_url!r})"
