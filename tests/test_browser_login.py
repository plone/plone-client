from collections.abc import Callable
from plone_client import browser_login
from plone_client.browser_login import login_url
from plone_client.exceptions import PloneConfigurationError
from urllib.parse import parse_qsl
from urllib.parse import urlsplit

import httpx
import pytest
import socket
import threading


SITE = "https://example.org"
# A request the fake frontend sends: (listener URL, state) -> (method, url, kwargs)
Request = Callable[[str, str], tuple[str, str, dict]]


def post(token: str = "the-token", state: str | None = None) -> Request:
    """The handoff form, with the right state unless another one is given."""

    def make(listener: str, expected: str) -> tuple[str, str, dict]:
        data = {"token": token, "state": expected if state is None else state}
        return "POST", listener, {"data": data}

    return make


class Frontend:
    """Plays the site's frontend: reads the login URL and calls the listener."""

    def __init__(self, *requests: Request) -> None:
        self.requests = requests
        self.responses: list[httpx.Response] = []
        self.url = ""
        self.thread: threading.Thread | None = None

    def __call__(self, url: str) -> bool:
        self.url = url
        self.thread = threading.Thread(target=self._send, daemon=True)
        self.thread.start()
        return True

    @property
    def query(self) -> dict[str, str]:
        return dict(parse_qsl(urlsplit(self.url).query))

    def _send(self) -> None:
        listener, state = self.query["return_url"], self.query["state"]
        for make in self.requests:
            method, url, kwargs = make(listener, state)
            self.responses.append(httpx.request(method, url, timeout=5, **kwargs))

    def done(self) -> list[httpx.Response]:
        if self.thread is not None:
            self.thread.join(5)
        return self.responses


def _login(frontend: Frontend, **kwargs) -> str:
    return browser_login.browser_login(
        SITE, announce=frontend, open_browser=False, timeout=5, **kwargs
    )


def test_login_url():
    url = login_url("https://example.org/", "http://127.0.0.1:5000/callback", "s t")
    assert url == (
        "https://example.org/login?return_url=http%3A%2F%2F127.0.0.1%3A5000"
        "%2Fcallback&state=s+t"
    )


def test_the_token_is_handed_over():
    frontend = Frontend(post("the-token"))
    assert _login(frontend) == "the-token"
    (response,) = frontend.done()
    assert response.status_code == 200
    assert "logged in" in response.text
    assert "the-token" not in response.text
    assert response.headers["Cache-Control"] == "no-store"


def test_the_login_page_names_a_loopback_listener():
    frontend = Frontend(post())
    _login(frontend)
    assert frontend.url.startswith(f"{SITE}/login?")
    listener = urlsplit(frontend.query["return_url"])
    assert (listener.scheme, listener.hostname, listener.path) == (
        "http",
        "127.0.0.1",
        "/callback",
    )
    assert listener.port
    assert len(frontend.query["state"]) >= 32


def test_the_listener_binds_the_loopback_address_only():
    with browser_login._Server(0, "state") as server:
        assert server.server_address[0] == "127.0.0.1"


def test_each_login_has_its_own_state():
    first, second = Frontend(post()), Frontend(post())
    _login(first)
    _login(second)
    assert first.query["state"] != second.query["state"]


def test_the_listener_waits_on_the_given_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    frontend = Frontend(post())
    _login(frontend, port=port)
    assert urlsplit(frontend.query["return_url"]).port == port


@pytest.mark.parametrize(
    "bad,status",
    [
        (post(state="another-state"), 400),
        (post(state=""), 400),
        (post(token=""), 400),
        (lambda listener, state: ("GET", listener, {}), 404),
        (
            lambda listener, state: (
                "POST",
                listener.replace("/callback", "/other"),
                {"data": {"token": "t", "state": state}},
            ),
            404,
        ),
        (
            lambda listener, state: (
                "POST",
                listener,
                {"json": {"token": "t", "state": state}},
            ),
            415,
        ),
        (
            lambda listener, state: (
                "POST",
                listener,
                {"data": {"token": "x" * (70 * 1024), "state": state}},
            ),
            400,
        ),
    ],
)
def test_a_refused_request_keeps_the_listener_waiting(bad, status):
    frontend = Frontend(bad, post("the-token"))
    assert _login(frontend) == "the-token"
    refused, accepted = frontend.done()
    assert refused.status_code == status
    assert accepted.status_code == 200


def test_no_login_in_time():
    with pytest.raises(PloneConfigurationError, match="No login arrived within"):
        browser_login.browser_login(
            SITE, announce=lambda url: None, open_browser=False, timeout=0.2
        )


def test_a_port_in_use():
    with socket.socket() as taken:
        taken.bind(("127.0.0.1", 0))
        taken.listen()
        port = taken.getsockname()[1]
        with pytest.raises(PloneConfigurationError, match=f"127.0.0.1:{port}"):
            browser_login.browser_login(SITE, port=port, open_browser=False)


def test_the_browser_is_opened(monkeypatch):
    frontend = Frontend(post("the-token"))
    monkeypatch.setattr(browser_login.webbrowser, "open", frontend)
    found = browser_login.browser_login(SITE, open_browser=True, timeout=5)
    assert found == "the-token"
    assert frontend.url.startswith(f"{SITE}/login?")


def test_the_browser_is_not_opened_by_default(monkeypatch):
    opened = []
    monkeypatch.setattr(browser_login.webbrowser, "open", opened.append)
    frontend = Frontend(post("the-token"))
    assert (
        browser_login.browser_login(SITE, announce=frontend, timeout=5) == "the-token"
    )
    assert opened == []
