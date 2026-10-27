"""Exceptions raised by plone-client.

Every exception derives from :class:`PloneClientError`, so a single
``except PloneClientError`` catches anything the library raises.
Errors answered by the site derive from :class:`PloneAPIError` and carry the
status code, the error type reported by ``plone.restapi`` and the parsed body.
"""

from typing import Any

import httpx


class PloneClientError(Exception):
    """Base class for every error raised by plone-client."""


class PloneConfigurationError(PloneClientError):
    """The client, a profile or a secret is missing or invalid."""


class PloneReadOnlyError(PloneClientError):
    """A request that changes the site was refused by a read-only client."""


class PloneConnectionError(PloneClientError):
    """The site could not be reached."""


class PloneTimeoutError(PloneConnectionError):
    """The site did not answer in time."""


class PloneOperationError(PloneClientError):
    """An operation of several requests stopped part way.

    The error that stopped it is the ``__cause__``.

    :param message: What failed.
    :param result: What the operation did before it stopped: the items it
        created or changed and every request it sent, so a caller can clean
        up or resume (see :class:`~plone_client.operations.OperationResult`).
    """

    def __init__(self, message: str, result: Any) -> None:
        super().__init__(message)
        self.result = result


class PloneAPIError(PloneClientError):
    """The site answered with an error status.

    :param message: Error message, taken from the response when possible.
    :param status_code: HTTP status code of the response.
    :param error_type: Error type reported by ``plone.restapi``
        (``NotFound``, ``BadRequest``, ``Unauthorized``…), if any.
    :param body: Parsed JSON body, or the response text.
    :param method: HTTP method of the failed request.
    :param url: URL of the failed request.
    """

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        error_type: str = "",
        body: Any = None,
        method: str = "",
        url: str = "",
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_type = error_type
        self.body = body
        self.method = method
        self.url = url

    def __str__(self) -> str:
        prefix = f"{self.method} {self.url}: " if self.method else ""
        return f"{prefix}HTTP {self.status_code} {self.message}"

    def to_dict(self) -> dict[str, Any]:
        """Serializable summary of the error.

        :returns: Status code, error type, message, method and URL.
        """
        return {
            "status_code": self.status_code,
            "type": self.error_type or self.__class__.__name__,
            "message": self.message,
            "method": self.method,
            "url": self.url,
        }


class PloneBadRequestError(PloneAPIError):
    """HTTP 400: invalid data, such as a validation error or a duplicated id."""


class PloneAuthenticationError(PloneAPIError):
    """HTTP 401: the credentials are missing, wrong or expired."""


class PloneForbiddenError(PloneAPIError):
    """HTTP 403: the user is not allowed to do this, or the item is locked."""


class PloneNotFoundError(PloneAPIError):
    """HTTP 404: there is nothing at this path."""


class PloneConflictError(PloneAPIError):
    """HTTP 409: the request conflicts with the current state."""


class PloneServerError(PloneAPIError):
    """HTTP 5xx: the site failed to handle the request."""


_STATUS_ERRORS: dict[int, type[PloneAPIError]] = {
    400: PloneBadRequestError,
    401: PloneAuthenticationError,
    403: PloneForbiddenError,
    404: PloneNotFoundError,
    409: PloneConflictError,
}


def _error_details(body: Any, default: str) -> tuple[str, str]:
    """Message and type from a ``plone.restapi`` error body.

    ``plone.restapi`` answers either ``{"type": …, "message": …}`` or
    ``{"error": {"type": …, "message": …}}``.

    :param body: Parsed JSON body or response text.
    :param default: Message used when the body has none.
    :returns: The message and the error type.
    """
    if isinstance(body, dict):
        details = body["error"] if isinstance(body.get("error"), dict) else body
        message = details.get("message") or default
        return str(message), str(details.get("type") or "")
    if isinstance(body, str) and body.strip():
        return body.strip()[:500], ""
    return default, ""


def error_payload(error: PloneClientError) -> dict[str, Any]:
    """JSON description of an error, as the command line and MCP server report it.

    :param error: The error.
    :returns: ``{"error": {...}}`` with the type and message, and the status
        code and URL for errors answered by the site. For an operation that
        stopped part way, ``error`` describes the request that failed and
        ``result`` what the operation had done.
    """
    cause = error.__cause__
    if isinstance(error, PloneOperationError) and isinstance(cause, PloneClientError):
        return {**error_payload(cause), "result": error.result.to_dict()}
    if isinstance(error, PloneAPIError):
        return {"error": error.to_dict()}
    return {"error": {"type": error.__class__.__name__, "message": str(error)}}


def error_from_response(response: httpx.Response) -> PloneAPIError:
    """Build the exception matching an error response.

    :param response: Response with a status code of 400 or more.
    :returns: An instance of the :class:`PloneAPIError` subclass for the status.
    """
    try:
        body: Any = response.json()
    except ValueError:
        body = response.text
    message, error_type = _error_details(body, response.reason_phrase)
    status = response.status_code
    error_class = _STATUS_ERRORS.get(status)
    if error_class is None:
        error_class = PloneServerError if status >= 500 else PloneAPIError
    return error_class(
        message,
        status_code=status,
        error_type=error_type,
        body=body,
        method=response.request.method,
        url=str(response.request.url),
    )
