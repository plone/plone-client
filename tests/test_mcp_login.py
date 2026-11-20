from . import expiring_jwt
from . import SITE_URL
from .test_browser_login import Frontend
from .test_browser_login import post
from .test_mcp_server import call
from .test_mcp_server import tool_error
from .test_mcp_server import tools
from functools import partial
from plone_client import mcp_server
from plone_client import PloneClient
from plone_client.browser_login import PendingLogin
from plone_client.profiles import Profile

import pytest


FRONTEND_URL = "http://www.plone.test"
OTHER_URL = "http://other.test/Plone"
KEY = ("plone-client:sso", "token")
LOGGED_IN = {"user": [{"id": "logout", "title": "Log out"}]}


@pytest.fixture
def sites(site, memory_keyring):
    """Build the sites of a token profile and a basic profile."""

    def build(*profiles: Profile, dry_run: bool = False) -> mcp_server.Sites:
        def factory(**settings):
            return PloneClient(**{
                **settings,
                "transport": site.transport,
                "retries": 0,
            })

        return mcp_server.Sites.from_profiles(
            profiles or (SSO,), dry_run=dry_run, factory=factory
        )

    return build


SSO = Profile(name="sso", url=SITE_URL, auth="token", frontend_url=FRONTEND_URL)
BASIC = Profile(name="docs", url=OTHER_URL, username="editor")


@pytest.fixture
def quick(monkeypatch):
    """Make a waiting login call return at once."""
    monkeypatch.setattr(mcp_server, "LOGIN_WAIT", 0.05)


def _start(server, **arguments) -> Frontend:
    """Call login once, and return a frontend for the URL it gave."""
    result = call(server, "login", **arguments)
    assert result["status"] == "started"
    frontend = Frontend()
    frontend.url = result["url"]
    return frontend


def _hand_over(frontend: Frontend, token: str) -> None:
    """Post the token to the waiting listener."""
    frontend.requests = (post(token),)
    frontend(frontend.url)
    (answer,) = frontend.done()
    assert answer.status_code == 200


def test_login_is_offered_for_a_token_profile_in_the_keyring(sites):
    found = tools(mcp_server.build_server(sites()))
    assert "login" in found
    assert found["login"].input_schema["properties"] == {}
    assert found["login"].annotations.destructive_hint is False


@pytest.mark.parametrize(
    "profile",
    [
        BASIC,
        Profile(name="env", url=SITE_URL, auth="token", secret="env"),
        Profile(
            name="cmd",
            url=SITE_URL,
            auth="token",
            secret="command",
            secret_command="op read op://token",
        ),
    ],
)
def test_login_is_not_offered_otherwise(sites, profile):
    server = mcp_server.build_server(sites(profile))
    assert "login" not in tools(server)
    assert "call `login`" not in server.instructions


def test_login_hands_the_token_over_and_stores_it(sites, site, memory_keyring):
    memory_keyring.store[KEY] = expiring_jwt(-60)
    built = sites()
    server = mcp_server.build_server(built)
    stale = built.client("sso")
    frontend = _start(server)
    assert frontend.url.startswith(f"{FRONTEND_URL}/login?")
    token = expiring_jwt(43_200, sub="maria")
    _hand_over(frontend, token)
    site.add("GET", "/@actions", LOGGED_IN)
    result = call(server, "login")
    assert result["status"] == "logged_in"
    assert result["username"] == "maria"
    assert memory_keyring.store[KEY] == token
    assert built.client("sso") is not stale
    assert site.last.headers["Authorization"] == f"Bearer {token}"
    assert built.site("sso").pending is None


def test_login_works_in_a_dry_run(sites, site, memory_keyring):
    server = mcp_server.build_server(sites(dry_run=True))
    frontend = _start(server)
    token = expiring_jwt(43_200)
    _hand_over(frontend, token)
    site.add("GET", "/@actions", LOGGED_IN)
    assert call(server, "login")["status"] == "logged_in"
    assert memory_keyring.store[KEY] == token


@pytest.mark.usefixtures("quick")
def test_login_reports_a_login_still_waiting(sites):
    built = sites()
    server = mcp_server.build_server(built)
    frontend = _start(server)
    result = call(server, "login")
    assert result["status"] == "waiting"
    assert result["url"] == frontend.url
    built.close()


@pytest.mark.usefixtures("quick")
def test_login_starts_again_after_a_login_that_ended(sites, monkeypatch):
    monkeypatch.setattr(mcp_server, "PendingLogin", partial(PendingLogin, timeout=0.1))
    built = sites()
    server = mcp_server.build_server(built)
    first = _start(server)
    built.site("sso").pending.wait(5)
    result = call(server, "login")
    assert result["status"] == "started"
    assert result["url"] != first.url
    assert result["message"].startswith("No login arrived within 0.1 seconds")
    built.close()


def test_login_refuses_a_token_that_is_not_a_jwt(sites, memory_keyring):
    server = mcp_server.build_server(sites())
    _hand_over(_start(server), "opaque")
    error = tool_error(server, "login")
    assert "not a JWT" in error["error"]["message"]
    assert KEY not in memory_keyring.store


def test_login_refuses_an_expired_token(sites, memory_keyring):
    server = mcp_server.build_server(sites())
    _hand_over(_start(server), expiring_jwt(-60))
    error = tool_error(server, "login")
    assert "token that expired at" in error["error"]["message"]
    assert KEY not in memory_keyring.store


def test_login_with_several_sites_takes_only_those_that_log_in(sites):
    built = sites(SSO, BASIC)
    server = mcp_server.build_server(built)
    schema = tools(server)["login"].input_schema["properties"]["site"]
    # One choice is written as const, several as enum
    assert schema.get("enum", [schema.get("const")]) == ["sso"]
    assert "for `sso`" in server.instructions
    assert call(server, "login", site="sso")["status"] == "started"
    built.close()


def test_login_refuses_a_site_without_it(sites):
    built = sites(SSO, BASIC)
    login = mcp_server._login_tool(built)
    with pytest.raises(mcp_server.PloneConfigurationError, match="set-secret docs"):
        login(site="docs")


def test_a_refused_token_points_to_login(sites, site, memory_keyring):
    memory_keyring.store[KEY] = expiring_jwt(600)
    site.add("GET", "/news", {"message": "Unauthorized"}, status=401)
    error = tool_error(mcp_server.build_server(sites()), "get_content", path="/news")
    assert error["error"]["status_code"] == 401
    assert error["error"]["hint"] == mcp_server.LOGIN_HINT


def test_other_sites_get_no_login_hint(sites, site, memory_keyring):
    memory_keyring.store[("plone-client:docs", "editor")] = "secret"
    site.add("GET", "/news", {"message": "Unauthorized"}, status=401)
    error = tool_error(
        mcp_server.build_server(sites(BASIC)), "get_content", path="/news"
    )
    assert error["error"]["status_code"] == 401
    assert "hint" not in error["error"]


def test_instructions_explain_the_login(sites):
    instructions = mcp_server.build_server(sites()).instructions
    assert "call `login`" in instructions
    assert "Never open the URL yourself." in instructions


def test_rejected_token_site_is_told_to_log_in(sites):
    server = mcp_server.build_server(sites(SSO, BASIC), rejected=("sso", "docs"))
    assert "`sso` were rejected" in server.instructions
    assert "Call `login` to log in again." in server.instructions
    assert "plone-client profile set-secret docs" in server.instructions
    assert "plone-client profile set-secret sso" not in server.instructions


def test_only_some_tools_can_leave_login_out(sites):
    server = mcp_server.build_server(sites(), tools=["search"])
    assert set(tools(server)) == {"search"}
    server = mcp_server.build_server(sites(), tools=["login"])
    assert set(tools(server)) == {"login"}


def test_close_stops_a_waiting_login(sites):
    built = sites()
    server = mcp_server.build_server(built)
    _start(server)
    pending = built.site("sso").pending
    built.close()
    assert pending.done
    assert pending.error == "The login was cancelled"
    assert built.site("sso").pending is None
