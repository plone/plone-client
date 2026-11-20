"""Log in through the site's own login page, in a browser.

For sites where people log in through another provider (Google, GitHub, an
organization's OpenID Connect server) and have no Plone password. The site's
frontend runs its usual login, asks the user to allow an application on this
computer to act for them, and posts the token to a listener that plone-client
runs on ``127.0.0.1``. This needs a frontend that supports a loopback
``return_url``, such as volto-authomatic with
`collective/volto-authomatic#50
<https://github.com/collective/volto-authomatic/issues/50>`_.

The exchange:

1. plone-client listens on ``http://127.0.0.1:<port>/callback`` and picks a
   random ``state``.
2. It opens ``<site>/login?return_url=<listener>&state=<state>``.
3. After the login and the user's consent, the frontend sends a form
   ``POST`` to the listener with the fields ``token`` and ``state``.
4. plone-client accepts the token only when ``state`` matches.

The token never appears in a URL, and the listener only answers on the
loopback address.
"""

from .exceptions import PloneConfigurationError
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler
from socketserver import TCPServer
from typing import Any
from urllib.parse import parse_qs
from urllib.parse import urlencode

import logging
import secrets
import threading
import time
import webbrowser


logger = logging.getLogger("plone_client")

#: Path of the listener that receives the token.
CALLBACK_PATH = "/callback"
#: Largest form body the listener reads, in bytes.
MAX_BODY = 64 * 1024
#: Seconds the listener waits for the login by default.
DEFAULT_TIMEOUT = 300.0

FORM = "application/x-www-form-urlencoded"
PAGE = (
    "<!doctype html><html><head><meta charset='utf-8'>"
    "<title>plone-client</title></head><body><p>{message}</p></body></html>"
)


def login_url(site_url: str, return_url: str, state: str) -> str:
    """URL of the site's login page that hands the token to a listener.

    :param site_url: URL of the site's frontend.
    :param return_url: URL of the listener.
    :param state: The value the frontend sends back with the token.
    :returns: ``<site_url>/login?return_url=…&state=…``.
    """
    query = urlencode({"return_url": return_url, "state": state})
    return f"{site_url.rstrip('/')}/login?{query}"


class _Server(TCPServer):
    """A listener on ``127.0.0.1`` that waits for one token.

    :param port: Port to listen on; ``0`` picks a free one.
    :param state: The value a request must carry to be accepted.
    """

    def __init__(self, port: int, state: str) -> None:
        super().__init__(("127.0.0.1", port), _Handler)
        self.state = state
        self.token = ""


class _Handler(BaseHTTPRequestHandler):
    """Accept the form ``POST`` that carries the token."""

    server: _Server
    # Seconds a connection may take to send its request.
    timeout = 10

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        """Log requests at debug level instead of printing them."""
        logger.debug("Login listener: " + format, *args)

    def _answer(self, status: int, message: str) -> None:
        """Send a short HTML page.

        :param status: HTTP status.
        :param message: Text of the page.
        """
        body = PAGE.format(message=message).encode()
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        """Refuse anything but the form ``POST``."""
        self._answer(404, "Not found.")

    def _form(self) -> dict[str, list[str]] | None:
        """Read the form, or answer with an error.

        :returns: The fields, or ``None`` when an error was sent.
        """
        if self.path.split("?", 1)[0] != CALLBACK_PATH:
            self._answer(404, "Not found.")
            return None
        content_type = self.headers.get("Content-Type", "").split(";")[0]
        if content_type.strip().lower() != FORM:
            self._answer(415, "The login must be sent as a form.")
            return None
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            length = -1
        if not 0 < length <= MAX_BODY:
            self._answer(400, "The login form is empty or too large.")
            return None
        return parse_qs(self.rfile.read(length).decode("utf-8", "replace"))

    def do_POST(self) -> None:
        """Take the token when the request carries the expected ``state``."""
        form = self._form()
        if form is None:
            return
        state = form.get("state", [""])[0]
        token = form.get("token", [""])[0]
        if not secrets.compare_digest(state.encode(), self.server.state.encode()):
            logger.warning("Login listener: refused a request with another state")
            self._answer(400, "This login does not belong to the waiting command.")
            return
        if not token:
            self._answer(400, "The login carried no token.")
            return
        self.server.token = token
        self._answer(
            200,
            "You are logged in. Close this tab and go back to plone-client, "
            "in the terminal or your assistant.",
        )


class PendingLogin:
    """A browser login whose listener waits in a background thread.

    The listener starts at once, so ``url`` can be shown to the user while
    the caller does something else, such as answering an MCP tool call.

    :param site_url: URL of the site's frontend, whose ``/login`` page runs
        the login.
    :param port: Port of the listener on ``127.0.0.1``; ``0`` picks a free one.
    :param timeout: Seconds the listener waits for the login.
    :raises PloneConfigurationError: If the port cannot be used.
    """

    #: Longest a listener waits for one request, so it notices a cancel.
    TICK = 0.5

    def __init__(
        self, site_url: str, *, port: int = 0, timeout: float = DEFAULT_TIMEOUT
    ) -> None:
        state = secrets.token_urlsafe(32)
        try:
            self._server = _Server(port, state)
        except OSError as exc:
            raise PloneConfigurationError(
                f"Cannot listen on 127.0.0.1:{port}: {exc.strerror or exc}"
            ) from exc
        listener = f"http://127.0.0.1:{self._server.server_address[1]}{CALLBACK_PATH}"
        self.url = login_url(site_url, listener, state)
        self.timeout = timeout
        #: The token, once the site has handed it over.
        self.token = ""
        #: Why the login ended without a token, once it has.
        self.error = ""
        self._deadline = time.monotonic() + timeout
        self._done = threading.Event()
        threading.Thread(target=self._listen, daemon=True).start()

    def _listen(self) -> None:
        """Answer requests until the token arrives or the time is up."""
        try:
            while not self._server.token:
                remaining = self._deadline - time.monotonic()
                if remaining <= 0:
                    self.error = (
                        f"No login arrived within {self.timeout:g} seconds; the "
                        "site's frontend must support a loopback return_url"
                    )
                    return
                self._server.timeout = min(remaining, self.TICK)
                self._server.handle_request()
            self.token = self._server.token
        finally:
            self._server.server_close()
            self._done.set()

    @property
    def done(self) -> bool:
        """Whether the login has ended, with a token or an error."""
        return self._done.is_set()

    def wait(self, timeout: float | None = None) -> bool:
        """Wait for the login to end.

        :param timeout: Seconds to wait; ``None`` until it ends.
        :returns: Whether it has ended.
        """
        return self._done.wait(timeout)

    def cancel(self) -> None:
        """Stop listening; the login ends with an error."""
        self._deadline = 0.0
        self.wait()
        if not self.token:
            self.error = "The login was cancelled"


def browser_login(
    site_url: str,
    *,
    port: int = 0,
    timeout: float = DEFAULT_TIMEOUT,
    open_browser: bool = False,
    announce: Callable[[str], None] | None = None,
) -> str:
    """Log in through the site's login page and return the token it hands over.

    :param site_url: URL of the site's frontend, whose ``/login`` page runs
        the login.
    :param port: Port of the listener on ``127.0.0.1``; ``0`` picks a free one.
    :param timeout: Seconds to wait for the login.
    :param open_browser: Also open the login page in the default browser,
        which may not be the one the user logs in to the site with.
    :param announce: Called with the login page's URL before waiting, so it
        can be shown to the user to open.
    :returns: The token.
    :raises PloneConfigurationError: If the port cannot be used, or no login
        arrives in time.
    """
    pending = PendingLogin(site_url, port=port, timeout=timeout)
    if announce is not None:
        announce(pending.url)
    if open_browser:
        webbrowser.open(pending.url)
    pending.wait()
    if not pending.token:
        raise PloneConfigurationError(pending.error)
    return pending.token
