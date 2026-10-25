"""
Exceptions for plone-client.

All exceptions derive from PloneClientError, allowing users to catch
all library errors with a single except clause.
"""

from __future__ import annotations

from typing import Any


class PloneClientError(Exception):
    """Base exception for all plone-client errors."""


class PloneAuthenticationError(PloneClientError):
    """Raised when authentication fails (HTTP 401)."""


class PloneForbiddenError(PloneClientError):
    """Raised when the user lacks permission (HTTP 403)."""


class PloneNotFoundError(PloneClientError):
    """Raised when a resource is not found (HTTP 404)."""


class PloneConflictError(PloneClientError):
    """Raised on resource conflict, e.g. duplicate id (HTTP 409)."""


class PloneServerError(PloneClientError):
    """Raised on server-side errors (HTTP 5xx)."""


class PloneConnectionError(PloneClientError):
    """Raised when the connection to the Plone server fails."""


class PloneTimeoutError(PloneClientError):
    """Raised when a request times out."""


class PloneAPIError(PloneClientError):
    """
    Raised for unexpected API responses.

    :ivar status_code: HTTP status code returned by the server.
    :vartype status_code: int or None
    :ivar response_body: Parsed JSON body (if available) or raw text.
    :vartype response_body: Any
    """

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: Any = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"{self.__class__.__name__}("
            f"message={self.args[0]!r}, "
            f"status_code={self.status_code!r})"
        )
