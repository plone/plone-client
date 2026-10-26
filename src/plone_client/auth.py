"""Authentication strategies for :class:`~plone_client.PloneClient`.

Three ways to authenticate against ``plone.restapi`` are supported:

* HTTP basic authentication (:class:`httpx.BasicAuth`), the simplest option
  and the default when a username and password are given;
* a JWT obtained from ``@login`` (:class:`JWTAuth`), which logs in again
  when the token expires;
* a token issued beforehand (:class:`TokenAuth`).

Any other :class:`httpx.Auth` can be passed to the client as well.
"""

from .exceptions import error_from_response
from collections.abc import Generator
from typing import Literal

import httpx


AuthMethod = Literal["basic", "jwt"]


class TokenAuth(httpx.Auth):
    """Send a token issued beforehand as ``Authorization: Bearer``.

    :param token: The JWT.
    """

    def __init__(self, token: str) -> None:
        self.token = token

    def auth_flow(
        self, request: httpx.Request
    ) -> Generator[httpx.Request, httpx.Response, None]:
        request.headers["Authorization"] = f"Bearer {self.token}"
        yield request


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
) -> httpx.Auth | None:
    """Pick the authentication for a set of credentials.

    A token wins over a username and password. Without any credential the
    client is anonymous.

    :param username: Login name.
    :param password: Password.
    :param token: JWT issued beforehand.
    :param method: ``basic`` or ``jwt``, used with a username and password.
    :param login_url: Absolute URL of ``@login``, needed by ``jwt``.
    :returns: The authentication, or ``None`` for anonymous access.
    :raises ValueError: If the method is unknown or only half of the
        username/password pair is given.
    """
    if token:
        return TokenAuth(token)
    if not (username or password):
        return None
    if not (username and password):
        raise ValueError("Both a username and a password are needed")
    if method == "basic":
        return httpx.BasicAuth(username, password)
    if method == "jwt":
        return JWTAuth(username, password, login_url)
    raise ValueError(f"Unknown authentication method: {method!r}")
