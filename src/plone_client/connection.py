"""
Low-level HTTP connection layer for plone-client.

Handles:
- Session management
- JWT authentication (``@login`` / ``@logout`` / ``@login-renew``)
- Automatic token renewal on 401 (single retry)
- Retry with exponential back-off + ``Retry-After`` header respect
- Rate-limit detection (HTTP 429)
- Request/response middleware hooks
- Optional correlation-ID / request-ID header injection
- Centralised error mapping
"""

from __future__ import annotations

import contextlib

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
from .logging_config import logger
from .logging_config import RequestLogger
from collections.abc import Callable
from requests import Response
from requests import Session
from requests.adapters import HTTPAdapter
from typing import Any
from urllib3.util.retry import Retry

import requests
import time
import uuid


_RETRYABLE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "DELETE"})
_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})

RequestHook = Callable[[str, str, dict[str, Any]], None]
ResponseHook = Callable[[str, str, Response, float], None]


class PloneConnection(RequestLogger):
    """
    Manages a :class:`requests.Session` against a Plone site.

    Middleware hooks
    ----------------
    Register callables via :meth:`add_request_hook` / :meth:`add_response_hook`::

        def audit(method, url, response, elapsed_ms):
            metrics.record(method, url, response.status_code, elapsed_ms)

        connection.add_response_hook(audit)

    Correlation IDs
    ---------------
    Set ``extra_headers={"X-Request-ID": "auto"}`` in config to attach a
    fresh UUID4 to every request automatically.
    """

    def __init__(self, config: PloneClientConfig) -> None:
        self._config = config
        self._session: Session = self._build_session()
        self._token: str = config.token
        self._request_hooks: list[RequestHook] = []
        self._response_hooks: list[ResponseHook] = []

    def _build_session(self) -> Session:
        session = Session()
        session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json",
        })
        if self._config.extra_headers:
            session.headers.update(self._config.extra_headers)
        session.verify = self._config.verify_ssl
        if self._config.proxies:
            session.proxies.update(self._config.proxies)
        urllib3_retry = Retry(
            total=self._config.max_retries,
            backoff_factor=self._config.retry_backoff,
            status_forcelist=(),
            allowed_methods=None,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=urllib3_retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        return session

    # ------------------------------------------------------------------
    # Middleware hooks
    # ------------------------------------------------------------------

    def add_request_hook(self, hook: RequestHook) -> None:
        """Register a callable invoked before every HTTP request.

        Signature: ``(method: str, url: str, kwargs: dict) -> None``
        """
        self._request_hooks.append(hook)

    def add_response_hook(self, hook: ResponseHook) -> None:
        """Register a callable invoked after every HTTP response.

        Signature: ``(method: str, url: str, response: Response,
        elapsed_ms: float) -> None``
        """
        self._response_hooks.append(hook)

    def _run_request_hooks(self, method: str, url: str, kwargs: dict[str, Any]) -> None:
        for hook in self._request_hooks:
            try:
                hook(method, url, kwargs)
            except Exception as exc:
                logger.warning("Request hook %r raised: %s", hook, exc)

    def _run_response_hooks(
        self, method: str, url: str, response: Response, elapsed_ms: float
    ) -> None:
        for hook in self._response_hooks:
            try:
                hook(method, url, response, elapsed_ms)
            except Exception as exc:
                logger.warning("Response hook %r raised: %s", hook, exc)

    # ------------------------------------------------------------------
    # Authentication
    # ------------------------------------------------------------------

    def login(self) -> None:
        """Authenticate via POST /@login and store the JWT token."""
        if not self._config.has_credentials:
            raise PloneClientError("Cannot login: no username/password configured.")
        logger.debug("Authenticating as %s", self._config.username)
        response = self._request(
            "POST",
            "/@login",
            json={"login": self._config.username, "password": self._config.password},
            _authenticate=False,
            _auto_renew=False,
        )
        data = response.json()
        self._token = data.get("token", "")
        if not self._token:
            raise PloneAuthenticationError("Login succeeded but no token was returned.")
        self._session.headers["Authorization"] = f"Bearer {self._token}"
        logger.info("Successfully authenticated as %s", self._config.username)

    def logout(self) -> None:
        """Send POST /@logout and clear the stored token."""
        if self._token:
            with contextlib.suppress(PloneClientError):
                self._request("POST", "/@logout", _auto_renew=False)
        self._token = ""
        self._session.headers.pop("Authorization", None)
        logger.info("Logged out")

    def renew_token(self) -> None:
        """Renew the current JWT token via POST /@login-renew."""
        response = self._request("POST", "/@login-renew", _auto_renew=False)
        data = response.json()
        new_token = data.get("token", "")
        if new_token:
            self._token = new_token
            self._session.headers["Authorization"] = f"Bearer {new_token}"
            logger.debug("Token renewed")

    @property
    def token(self) -> str:
        return self._token

    # ------------------------------------------------------------------
    # Public request helpers
    # ------------------------------------------------------------------

    def get(self, path: str, **kwargs: Any) -> Response:
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs: Any) -> Response:
        return self._request("POST", path, **kwargs)

    def patch(self, path: str, **kwargs: Any) -> Response:
        return self._request("PATCH", path, **kwargs)

    def put(self, path: str, **kwargs: Any) -> Response:
        return self._request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs: Any) -> Response:
        return self._request("DELETE", path, **kwargs)

    # ------------------------------------------------------------------
    # Core request / retry loop
    # ------------------------------------------------------------------

    def _request(  # noqa: C901
        self,
        method: str,
        path: str,
        *,
        _authenticate: bool = True,
        _auto_renew: bool = True,
        **kwargs: Any,
    ) -> Response:
        if _authenticate and self._token:
            self._session.headers["Authorization"] = f"Bearer {self._token}"

        url = self._build_url(path)
        kwargs.setdefault("timeout", self._config.timeout)

        # Auto-generate per-request correlation ID when configured
        if (self._config.extra_headers or {}).get("X-Request-ID") == "auto":
            kwargs.setdefault("headers", {})
            kwargs["headers"]["X-Request-ID"] = str(uuid.uuid4())

        last_exc: Exception | None = None
        method_upper = method.upper()
        is_idempotent = method_upper in _RETRYABLE_METHODS

        for attempt in range(self._config.max_retries + 1):
            if attempt:
                sleep_time = self._config.retry_backoff * (2 ** (attempt - 1))
                logger.debug("Back-off %.2fs (attempt %d)", sleep_time, attempt)
                time.sleep(sleep_time)

            try:
                self.log_request(method, url, **kwargs)
                self._run_request_hooks(method, url, kwargs)

                t0 = time.monotonic()
                response = self._session.request(method, url, **kwargs)
                elapsed = (time.monotonic() - t0) * 1000

                self.log_response(method, url, response.status_code, elapsed)
                self._run_response_hooks(method, url, response, elapsed)

            except requests.exceptions.Timeout as exc:
                last_exc = exc
                self.log_retry(attempt + 1, self._config.max_retries, "timeout")
                continue
            except requests.exceptions.ConnectionError as exc:
                last_exc = exc
                self.log_retry(attempt + 1, self._config.max_retries, str(exc))
                continue
            except requests.exceptions.RequestException as exc:
                raise PloneConnectionError(str(exc)) from exc

            # 401 → attempt token renewal once (attempt 0 only)
            if (
                response.status_code == 401
                and _auto_renew
                and _authenticate
                and self._config.has_credentials
                and attempt == 0
            ):
                logger.debug("Got 401 — attempting token renewal")
                try:
                    self.renew_token()
                    continue
                except PloneClientError:
                    pass

            # 429 → respect Retry-After header
            if response.status_code == 429 and attempt < self._config.max_retries:
                wait = _parse_retry_after(response)
                if wait > 0:
                    logger.warning("Rate limited — sleeping %.1fs (Retry-After)", wait)
                    time.sleep(wait)
                else:
                    # fall back to exponential back-off on next loop iteration
                    pass
                self.log_retry(attempt + 1, self._config.max_retries, "HTTP 429")
                last_exc = None
                continue

            # Status-based retry for idempotent methods only
            if (
                response.status_code in _RETRYABLE_STATUSES
                and is_idempotent
                and attempt < self._config.max_retries
            ):
                self.log_retry(
                    attempt + 1,
                    self._config.max_retries,
                    f"HTTP {response.status_code}",
                )
                last_exc = None
                continue

            return self._raise_for_status(response)

        if last_exc is not None:
            if isinstance(last_exc, requests.exceptions.Timeout):
                raise PloneTimeoutError(
                    f"Request timed out after {self._config.max_retries} retries."
                ) from last_exc
            raise PloneConnectionError(str(last_exc)) from last_exc

        raise PloneClientError("Request failed after all retries.")  # pragma: no cover

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        return f"{self._config.base_url}/{path.lstrip('/')}"

    @staticmethod
    def _raise_for_status(response: Response) -> Response:
        status = response.status_code
        if status < 400:
            return response
        try:
            body: Any = response.json()
        except Exception:
            body = response.text
        message = (
            body.get("message", response.reason)
            if isinstance(body, dict)
            else str(body)
        )
        mapping = {
            401: PloneAuthenticationError,
            403: PloneForbiddenError,
            404: PloneNotFoundError,
            409: PloneConflictError,
        }
        exc_class = mapping.get(status)
        if exc_class:
            raise exc_class(message)
        if status >= 500:
            raise PloneServerError(f"Server error {status}: {message}")
        raise PloneAPIError(message, status_code=status, response_body=body)

    def __enter__(self) -> PloneConnection:
        return self

    def __exit__(self, *_: Any) -> None:
        self._session.close()


def _parse_retry_after(response: Response) -> float:
    """Parse Retry-After header; returns seconds to wait (0.0 if absent/invalid)."""
    header = response.headers.get("Retry-After", "")
    if not header:
        return 0.0
    try:
        return max(0.0, float(header))
    except ValueError:
        pass
    try:
        import email.utils

        t = email.utils.parsedate_to_datetime(header).timestamp()
        return max(0.0, t - time.time())
    except Exception:
        return 0.0
