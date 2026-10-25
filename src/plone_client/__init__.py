"""
plone-client — A Python client for Plone sites via plone.restapi.

Quick start::

    from plone_client import PloneClient

    with PloneClient(
        "https://my.plone.site", username="admin", password="secret"
    ) as client:
        doc = client.content.get("/front-page")
        results = client.search.search({"portal_type": "Document"})
"""

from .client import PloneClient
from .config import PloneClientConfig
from .exceptions import PloneAPIError
from .exceptions import PloneAuthenticationError
from .exceptions import PloneClientError
from .exceptions import PloneConflictError
from .exceptions import PloneConnectionError
from .exceptions import PloneForbiddenError
from .exceptions import PloneNotFoundError
from .exceptions import PloneServerError
from .exceptions import PloneTimeoutError
from .logging_config import set_logger
from .logging_config import setup_logging
from .pagination import BatchResult
from .pagination import paginate


__version__ = "0.1.0"

__all__ = [
    "AsyncPloneClient",
    "BatchResult",
    "PloneAPIError",
    "PloneAuthenticationError",
    "PloneClient",
    "PloneClientConfig",
    "PloneClientError",
    "PloneConflictError",
    "PloneConnectionError",
    "PloneForbiddenError",
    "PloneNotFoundError",
    "PloneServerError",
    "PloneTimeoutError",
    "paginate",
    "set_logger",
    "setup_logging",
]


def __getattr__(name: str) -> object:
    if name == "AsyncPloneClient":
        from .async_client import AsyncPloneClient

        return AsyncPloneClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
