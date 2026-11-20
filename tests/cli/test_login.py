from .. import expiring_jwt
from .. import SITE_URL
from ..test_browser_login import Frontend
from ..test_browser_login import post
from plone_client import browser_login
from plone_client.cli import site as site_commands
from plone_client.profiles import load_config

import pytest


pytestmark = pytest.mark.usefixtures("config_file")

KEY = ("plone-client:sso", "token")
LOGGED_IN = {"user": [{"id": "logout", "title": "Log out"}]}
ANONYMOUS = {"user": [{"id": "login", "title": "Log in"}]}


def _add_token_profile(invoke, token, *extra):
    run = invoke(
        "profile",
        "add",
        "sso",
        "--url",
        SITE_URL,
        "--auth",
        "token",
        "--password-stdin",
        *extra,
        stdin=f"{token}\n",
    )
    assert run.exit_code == 0, run.stderr
    return run


def test_login_stores_the_token_and_reports_it(invoke, memory_keyring, site):
    _add_token_profile(invoke, expiring_jwt(-60))
    token = expiring_jwt(43_200, sub="maria")
    site.add("GET", "/@actions", LOGGED_IN)
    site.add("GET", "/@system", {"plone_version": "6.1.5"})
    run = invoke("login", "sso", "--token-stdin", stdin=f"{token}\n")
    assert run.exit_code == 0, run.stderr
    assert memory_keyring.store[KEY] == token
    result = run.json
    assert result.pop("token_expires").endswith("+00:00")
    assert result == {
        "profile": "sso",
        "url": SITE_URL,
        "authenticated": True,
        "username": "maria",
        "token_subject": "maria",
        "credentials_rejected": False,
        "read_only": False,
        "plone_version": "6.1.5",
    }
    assert site.requests[0].headers["Authorization"] == f"Bearer {token}"


def test_login_uses_the_current_profile(invoke, memory_keyring, site):
    _add_token_profile(invoke, expiring_jwt(-60), "--use")
    token = expiring_jwt(43_200)
    site.add("GET", "/@actions", LOGGED_IN)
    run = invoke("login", "--token-stdin", stdin=f"{token}\n")
    assert run.exit_code == 0, run.stderr
    assert memory_keyring.store[KEY] == token


def test_login_refuses_a_password_profile(invoke, memory_keyring):
    invoke(
        "profile",
        "add",
        "blog",
        "--url",
        SITE_URL,
        "--username",
        "editor",
        "--password-stdin",
        stdin="s3cret\n",
    )
    run = invoke("login", "blog", "--token-stdin", stdin=f"{expiring_jwt(600)}\n")
    assert run.exit_code == 3
    assert "not with a token" in run.error["message"]
    assert memory_keyring.store[("plone-client:blog", "editor")] == "s3cret"


def test_login_refuses_an_expired_token(invoke, memory_keyring):
    old = expiring_jwt(600)
    _add_token_profile(invoke, old)
    run = invoke("login", "sso", "--token-stdin", stdin=f"{expiring_jwt(-60)}\n")
    assert run.exit_code == 3
    assert "The token expired at" in run.error["message"]
    assert memory_keyring.store[KEY] == old


def test_login_refuses_a_token_that_is_not_a_jwt(invoke, memory_keyring):
    old = expiring_jwt(600)
    _add_token_profile(invoke, old)
    run = invoke("login", "sso", "--token-stdin", stdin="opaque-token\n")
    assert run.exit_code == 3
    assert "--opaque" in run.error["message"]
    assert memory_keyring.store[KEY] == old


def test_login_with_opaque_stores_any_token(invoke, memory_keyring, site):
    _add_token_profile(invoke, expiring_jwt(600))
    site.add("GET", "/@actions", LOGGED_IN)
    run = invoke("login", "sso", "--token-stdin", "--opaque", stdin="opaque-token\n")
    assert run.exit_code == 0, run.stderr
    assert memory_keyring.store[KEY] == "opaque-token"
    assert "token_expires" not in run.json


def test_login_with_a_rejected_token(invoke, memory_keyring, site):
    _add_token_profile(invoke, expiring_jwt(600))
    token = expiring_jwt(43_200)
    site.add("GET", "/@actions", ANONYMOUS)
    run = invoke("login", "sso", "--token-stdin", stdin=f"{token}\n")
    assert run.exit_code == 4
    assert run.json["credentials_rejected"] is True
    assert memory_keyring.store[KEY] == token


def test_add_with_renew_margin(invoke, memory_keyring, config_file):
    run = _add_token_profile(invoke, expiring_jwt(600), "--renew-margin", "900")
    assert run.json["renew_margin"] == 900
    assert load_config(config_file).get("sso").renew_margin == 900


def test_a_command_renews_the_token_in_the_keyring(invoke, memory_keyring, site):
    old, new = expiring_jwt(600), expiring_jwt(43_200)
    _add_token_profile(invoke, old, "--use")
    site.add("POST", "/@login-renew", {"token": new})
    site.add("GET", "/@actions", LOGGED_IN)
    run = invoke("info")
    assert run.exit_code == 0, run.stderr
    assert memory_keyring.store[KEY] == new
    assert run.json["token_expires"] is not None


def test_renew_margin_zero_keeps_the_token(invoke, memory_keyring, site):
    old = expiring_jwt(600)
    _add_token_profile(invoke, old, "--use", "--renew-margin", "0")
    site.add("GET", "/@actions", LOGGED_IN)
    invoke("info")
    assert memory_keyring.store[KEY] == old
    assert "/@login-renew" not in [site.site_path(r) for r in site.requests]


def test_browser_login_stores_the_handed_over_token(invoke, memory_keyring, site):
    _add_token_profile(invoke, expiring_jwt(-60))
    token = expiring_jwt(43_200, sub="maria")
    frontend = Frontend(post(token))
    site.add("GET", "/@actions", LOGGED_IN)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(browser_login.webbrowser, "open", frontend)
        run = invoke("login", "sso", "--browser", "--open", "--timeout", "5")
    assert run.exit_code == 0, run.stderr
    assert memory_keyring.store[KEY] == token
    assert run.json["username"] == "maria"
    assert frontend.url.startswith(f"{SITE_URL}/login?")
    assert f"\n{frontend.url}\n" in run.stderr


def test_browser_login_only_prints_the_url(invoke, memory_keyring, monkeypatch):
    calls = []

    def fake(site_url, **kwargs):
        calls.append(kwargs)
        return expiring_jwt(43_200)

    monkeypatch.setattr(site_commands, "browser_login", fake)
    _add_token_profile(invoke, expiring_jwt(600))
    invoke("login", "sso", "--browser")
    (kwargs,) = calls
    assert kwargs["open_browser"] is False


def test_browser_login_uses_the_frontend_url(invoke, memory_keyring, monkeypatch):
    calls = []

    def fake(site_url, **kwargs):
        calls.append((site_url, kwargs))
        return expiring_jwt(43_200)

    monkeypatch.setattr(site_commands, "browser_login", fake)
    _add_token_profile(invoke, expiring_jwt(600), "--frontend-url", "https://www.x.org")
    invoke("login", "sso", "--browser", "--open", "--port", "51701")
    ((site_url, kwargs),) = calls
    assert site_url == "https://www.x.org"
    assert kwargs["port"] == 51701
    assert kwargs["open_browser"] is True


def test_browser_login_checks_the_token(invoke, memory_keyring, monkeypatch):
    old = expiring_jwt(600)
    monkeypatch.setattr(
        site_commands, "browser_login", lambda site_url, **kwargs: expiring_jwt(-60)
    )
    _add_token_profile(invoke, old)
    run = invoke("login", "sso", "--browser")
    assert run.exit_code == 3
    assert "The token expired at" in run.error["message"]
    assert memory_keyring.store[KEY] == old


def test_browser_login_excludes_token_stdin(invoke, memory_keyring):
    _add_token_profile(invoke, expiring_jwt(600))
    run = invoke("login", "sso", "--browser", "--token-stdin", stdin="x\n")
    assert run.exit_code == 2
