"""Authentication strategies for :class:`~plone_client.PloneClient`.

Three ways to authenticate against ``plone.restapi`` are supported:

* HTTP basic authentication (:class:`httpx.BasicAuth`), the simplest option
  and the default when a username and password are given;
* a JWT obtained from ``@login`` (:class:`JWTAuth`), which logs in again
  when the token expires;
* a token issued beforehand (:class:`TokenAuth`), which can renew itself
  with ``@login-renew`` before it expires.

Any other :class:`httpx.Auth` can be passed to the client as well.
"""

from .exceptions import error_from_response
from .exceptions import PloneClientError
from .tokens import expires_at
from .tokens import TokenStore
from collections.abc import Generator
from datetime import datetime
from datetime import UTC
from typing import Literal

import httpx
import logging
import threading


logger = logging.getLogger("plone_client")

AuthMethod = Literal["basic", "jwt"]


class TokenAuth(httpx.Auth):
    """Send a token issued beforehand as ``Authorization: Bearer``.

    With a ``renew_margin``, a JWT that expires within that many seconds is
    renewed with ``POST @login-renew`` before the request is sent, and the
    new token is used from then on. A token that already expired is not
    renewed: the site would refuse it. A renewal the site refuses is not
    tried again for the same token.

    With a ``store``, the renewed token is saved there. Before renewing, and
    when the site answers ``401``, the token in the store is taken instead
    when it expires later: another process sharing the store renewed it, and
    on a site that keeps a list of valid tokens, renewing deleted the old one.

    :param token: The JWT.
    :param renew_url: Absolute URL of the site's ``@login-renew`` service;
        renewal needs it.
    :param renew_margin: Renew the token when it expires within these
        seconds; ``None`` never renews.
    :param store: Where the token is kept between runs.
    """

    def __init__(
        self,
        token: str,
        *,
        renew_url: str = "",
        renew_margin: float | None = None,
        store: TokenStore | None = None,
    ) -> None:
        self.token = token
        self.renew_url = renew_url
        self.renew_margin = renew_margin
        self.store = store
        # The answer of @login-renew is read inside the flow.
        self.requires_response_body = self.renews
        self._tried = ""
        self._lock = threading.Lock()

    @property
    def renews(self) -> bool:
        """Whether the token is renewed before it expires."""
        return bool(self.renew_url) and self.renew_margin is not None

    def _due(self, now: datetime) -> bool:
        """Say whether the token should be renewed now.

        :param now: The current time, in UTC.
        :returns: ``True`` when the token expires within the margin and has
            not expired yet.
        """
        expires = expires_at(self.token)
        if expires is None or self.renew_margin is None:
            return False
        remaining = (expires - now).total_seconds()
        return 0 < remaining < self.renew_margin

    def _adopt_stored(self) -> bool:
        """Use the token in the store when it expires later than this one.

        :returns: ``True`` if the token changed.
        """
        if self.store is None:
            return False
        try:
            stored = self.store.load()
        except PloneClientError as exc:
            logger.warning("The stored token could not be read: %s", exc)
            return False
        if not stored or stored == self.token:
            return False
        new, old = expires_at(stored), expires_at(self.token)
        if new is None or (old is not None and new <= old):
            return False
        self.token = stored
        return True

    def _renew(self) -> Generator[httpx.Request, httpx.Response, None]:
        """Ask the site for a new token, and keep it."""
        self._tried = self.token
        response = yield httpx.Request(
            "POST",
            self.renew_url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self.token}",
            },
        )
        token = ""
        if response.status_code == 200:
            try:
                token = response.json().get("token", "")
            except (ValueError, AttributeError):
                token = ""
        if not token or not isinstance(token, str):
            logger.warning(
                "The site did not renew the token (status %s)", response.status_code
            )
            return
        self.token = token
        logger.debug("Renewed the token; it expires at %s", expires_at(token))
        if self.store is not None:
            try:
                self.store.save(token)
            except PloneClientError as exc:
                logger.warning("The renewed token could not be saved: %s", exc)

    def auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        if self.renews:
            with self._lock:
                now = datetime.now(UTC)
                if self._due(now):
                    self._adopt_stored()
                if self._due(now) and self._tried != self.token:
                    yield from self._renew()
        request.headers["Authorization"] = f"Bearer {self.token}"
        response = yield request
        if response.status_code != 401:
            return
        with self._lock:
            adopted = self._adopt_stored()
        if adopted:
            request.headers["Authorization"] = f"Bearer {self.token}"
            yield request
            return
        expires = expires_at(self.token)
        if expires is not None and expires <= datetime.now(UTC):
            logger.warning(
                "The token expired at %s; log in again to get a new one",
                expires.isoformat(),
            )


class JWTAuth(httpx.Auth):
    """Log in with ``POST @login`` and send the JWT it returns.

    The login happens on the first request. When the site answers ``401``,
    the token is assumed to be expired: the flow logs in again and repeats
    the request once.

    :param username: Login name.
    :param password: Password.
    :param login_url: Absolute URL of the site's ``@login`` service.
    """

    requires_response_body = True

    def __init__(self, username: str, password: str, login_url: str) -> None:
        self.username = username
        self.password = password
        self.login_url = login_url
        self.token = ""

    def _login(self) -> Generator[httpx.Request, httpx.Response, None]:
        """Ask the site for a new token.

        :raises PloneAuthenticationError: If the site refuses the credentials.
        """
        response = yield httpx.Request(
            "POST",
            self.login_url,
            json={"login": self.username, "password": self.password},
            headers={"Accept": "application/json"},
        )
        if response.status_code != 200:
            raise error_from_response(response)
        self.token = response.json().get("token", "")

    def auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        if not self.token:
            yield from self._login()
        request.headers["Authorization"] = f"Bearer {self.token}"
        response = yield request
        if response.status_code == 401:
            yield from self._login()
            request.headers["Authorization"] = f"Bearer {self.token}"
            yield request


def build_auth(
    *,
    username: str = "",
    password: str = "",
    token: str = "",
    method: AuthMethod = "basic",
    login_url: str = "",
    renew_url: str = "",
    renew_margin: float | None = None,
    token_store: TokenStore | None = None,
) -> httpx.Auth | None:
    """Pick the authentication for a set of credentials.

    A token wins over a username and password. Without any credential the
    client is anonymous.

    :param username: Login name.
    :param password: Password.
    :param token: JWT issued beforehand.
    :param method: ``basic`` or ``jwt``, used with a username and password.
    :param login_url: Absolute URL of ``@login``, needed by ``jwt``.
    :param renew_url: Absolute URL of ``@login-renew``, for a token.
    :param renew_margin: Renew a token that expires within these seconds;
        see :class:`TokenAuth`.
    :param token_store: Where a renewed token is saved.
    :returns: The authentication, or ``None`` for anonymous access.
    :raises ValueError: If the method is unknown or only half of the
        username/password pair is given.
    """
    if token:
        return TokenAuth(
            token,
            renew_url=renew_url,
            renew_margin=renew_margin,
            store=token_store,
        )
    if not (username or password):
        return None
    if not (username and password):
        raise ValueError("Both a username and a password are needed")
    if method == "basic":
        return httpx.BasicAuth(username, password)
    if method == "jwt":
        return JWTAuth(username, password, login_url)
    raise ValueError(f"Unknown authentication method: {method!r}")
