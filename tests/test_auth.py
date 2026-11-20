from . import expiring_jwt
from . import make_jwt
from plone_client import auth
from plone_client import tokens
from plone_client.exceptions import PloneAuthenticationError
from plone_client.exceptions import PloneConfigurationError

import httpx
import pytest


def test_jwt_logs_in_once(client_factory, site):
    site.add("POST", "/@login", {"token": "first"})
    client = client_factory(auth_method="jwt")
    client.get("/a")
    client.get("/b")
    methods = [(r.method, site.site_path(r)) for r in site.requests]
    assert methods == [("POST", "/@login"), ("GET", "/a"), ("GET", "/b")]
    assert site.body(site.requests[0]) == {"login": "admin", "password": "secret"}
    assert site.requests[1].headers["Authorization"] == "Bearer first"


def test_jwt_logs_in_again_when_expired(client_factory, site):
    site.add("POST", "/@login", {"token": "first"})
    site.add("POST", "/@login", {"token": "second"})
    site.add("GET", "/a", {"message": "expired"}, status=401)
    site.add("GET", "/a", {"title": "A"})
    client = client_factory(auth_method="jwt")
    assert client.get("/a") == {"title": "A"}
    assert [r.headers.get("Authorization") for r in site.requests] == [
        None,
        "Bearer first",
        None,
        "Bearer second",
    ]


def test_jwt_login_failure(client_factory, site):
    site.add(
        "POST",
        "/@login",
        {"type": "Unauthorized", "message": "Wrong login"},
        status=401,
    )
    client = client_factory(auth_method="jwt")
    with pytest.raises(PloneAuthenticationError, match="Wrong login"):
        client.get("/a")


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({}, type(None)),
        ({"token": "t"}, auth.TokenAuth),
        ({"token": "t", "username": "u", "password": "p"}, auth.TokenAuth),
        ({"username": "u", "password": "p"}, httpx.BasicAuth),
        ({"username": "u", "password": "p", "method": "jwt"}, auth.JWTAuth),
    ],
)
def test_build_auth(kwargs, expected):
    assert type(auth.build_auth(**kwargs)) is expected


@pytest.mark.parametrize(
    "kwargs,message",
    [
        ({"username": "u"}, "Both a username and a password"),
        ({"password": "p"}, "Both a username and a password"),
        (
            {"username": "u", "password": "p", "method": "digest"},
            "Unknown authentication",
        ),
    ],
)
def test_build_auth_errors(kwargs, message):
    with pytest.raises(ValueError, match=message):
        auth.build_auth(**kwargs)


class MemoryStore:
    """A token store kept in memory."""

    def __init__(self, token: str = "", fail: bool = False) -> None:
        self.token = token
        self.saved: list[str] = []
        self.fail = fail

    def load(self) -> str:
        if self.fail:
            raise PloneConfigurationError("no keyring")
        return self.token

    def save(self, token: str) -> None:
        if self.fail:
            raise PloneConfigurationError("no keyring")
        self.token = token
        self.saved.append(token)


@pytest.fixture
def token_client(client_factory):
    """Build clients that authenticate with a token and no password."""

    def factory(token: str, **kwargs):
        return client_factory(username="", password="", token=token, **kwargs)

    return factory


def _calls(site) -> list[tuple[str, str, str | None]]:
    """Method, path and Authorization header of each request."""
    return [
        (r.method, site.site_path(r), r.headers.get("Authorization"))
        for r in site.requests
    ]


def test_token_is_renewed_inside_the_margin(token_client, site):
    old, new = expiring_jwt(600), expiring_jwt(43_200)
    site.add("POST", "/@login-renew", {"token": new})
    client = token_client(old, renew_margin=3600)
    client.get("/a")
    client.get("/b")
    assert _calls(site) == [
        ("POST", "/@login-renew", f"Bearer {old}"),
        ("GET", "/a", f"Bearer {new}"),
        ("GET", "/b", f"Bearer {new}"),
    ]
    assert client.token_claims()["exp"] == tokens.claims(new)["exp"]


def test_token_is_not_renewed_outside_the_margin(token_client, site):
    token = expiring_jwt(7200)
    client = token_client(token, renew_margin=3600)
    client.get("/a")
    assert _calls(site) == [("GET", "/a", f"Bearer {token}")]


def test_token_is_not_renewed_without_a_margin(token_client, site):
    token = expiring_jwt(60)
    client = token_client(token)
    client.get("/a")
    assert _calls(site) == [("GET", "/a", f"Bearer {token}")]


@pytest.mark.parametrize("token", ["opaque-token", make_jwt(sub="editor")])
def test_token_without_an_expiry_is_not_renewed(token_client, site, token):
    client = token_client(token, renew_margin=3600)
    client.get("/a")
    assert _calls(site) == [("GET", "/a", f"Bearer {token}")]


def test_expired_token_is_not_renewed(token_client, site, caplog):
    token = expiring_jwt(-60)
    site.add("GET", "/a", {"message": "expired"}, status=401)
    client = token_client(token, renew_margin=3600)
    with pytest.raises(PloneAuthenticationError):
        client.get("/a")
    assert _calls(site) == [("GET", "/a", f"Bearer {token}")]
    assert "The token expired at" in caplog.text


def test_refused_renewal_is_tried_once(token_client, site, caplog):
    token = expiring_jwt(600)
    site.add("POST", "/@login-renew", {"message": "no"}, status=401)
    client = token_client(token, renew_margin=3600)
    client.get("/a")
    client.get("/b")
    assert _calls(site) == [
        ("POST", "/@login-renew", f"Bearer {token}"),
        ("GET", "/a", f"Bearer {token}"),
        ("GET", "/b", f"Bearer {token}"),
    ]
    assert "did not renew the token (status 401)" in caplog.text


@pytest.mark.parametrize("answer", [{}, {"token": ""}, {"token": 1}, ["token"]])
def test_renewal_without_a_token_keeps_the_old_one(token_client, site, answer):
    token = expiring_jwt(600)
    site.add("POST", "/@login-renew", answer)
    client = token_client(token, renew_margin=3600)
    client.get("/a")
    assert _calls(site)[-1] == ("GET", "/a", f"Bearer {token}")


def test_renewed_token_is_saved(token_client, site):
    old, new = expiring_jwt(600), expiring_jwt(43_200)
    site.add("POST", "/@login-renew", {"token": new})
    store = MemoryStore(old)
    client = token_client(old, renew_margin=3600, token_store=store)
    client.get("/a")
    assert store.saved == [new]


def test_store_that_fails_keeps_the_token_in_memory(token_client, site, caplog):
    old, new = expiring_jwt(600), expiring_jwt(43_200)
    site.add("POST", "/@login-renew", {"token": new})
    client = token_client(old, renew_margin=3600, token_store=MemoryStore(fail=True))
    client.get("/a")
    assert _calls(site)[-1] == ("GET", "/a", f"Bearer {new}")
    assert "could not be read" in caplog.text
    assert "could not be saved" in caplog.text


def test_token_renewed_by_another_process_is_used(token_client, site):
    old, newer = expiring_jwt(600), expiring_jwt(43_200)
    store = MemoryStore(newer)
    client = token_client(old, renew_margin=3600, token_store=store)
    client.get("/a")
    assert _calls(site) == [("GET", "/a", f"Bearer {newer}")]
    assert store.saved == []


def test_older_stored_token_is_ignored(token_client, site):
    old, new = expiring_jwt(600), expiring_jwt(43_200)
    site.add("POST", "/@login-renew", {"token": new})
    client = token_client(
        old, renew_margin=3600, token_store=MemoryStore(expiring_jwt(300))
    )
    client.get("/a")
    assert [call[:2] for call in _calls(site)] == [
        ("POST", "/@login-renew"),
        ("GET", "/a"),
    ]


def test_401_takes_the_token_another_process_renewed(token_client, site):
    old, newer = expiring_jwt(7200), expiring_jwt(43_200)
    site.add("GET", "/a", {"message": "deleted"}, status=401)
    site.add("GET", "/a", {"title": "A"})
    store = MemoryStore(old)
    client = token_client(old, renew_margin=3600, token_store=store)

    def renewed_elsewhere(request):
        store.token = newer
        return httpx.Response(401, json={"message": "deleted"})

    site.routes[("GET", "/a")][0] = renewed_elsewhere
    assert client.get("/a") == {"title": "A"}
    assert _calls(site) == [
        ("GET", "/a", f"Bearer {old}"),
        ("GET", "/a", f"Bearer {newer}"),
    ]


def test_401_without_a_newer_stored_token_is_not_repeated(token_client, site):
    token = expiring_jwt(7200)
    site.add("GET", "/a", {"message": "no"}, status=401)
    client = token_client(token, renew_margin=3600, token_store=MemoryStore(token))
    with pytest.raises(PloneAuthenticationError):
        client.get("/a")
    assert len(site.requests) == 1


@pytest.mark.parametrize("mode", [{"read_only": True}, {"dry_run": True}])
def test_read_only_and_dry_run_clients_still_renew(token_client, site, mode):
    old, new = expiring_jwt(600), expiring_jwt(43_200)
    site.add("POST", "/@login-renew", {"token": new})
    client = token_client(old, renew_margin=3600, **mode)
    client.get("/a")
    assert _calls(site)[-1] == ("GET", "/a", f"Bearer {new}")


def test_frontend_requests_use_the_renewed_token(token_client, site):
    old, new = expiring_jwt(600), expiring_jwt(43_200)
    site.add("POST", "/@login-renew", {"token": new})
    client = token_client(old, renew_margin=3600)
    client.get("/a")
    client.frontend_request("GET", "/@blocks-schema", raise_for_status=False)
    assert site.last.headers["Authorization"] == f"Bearer {new}"


def test_token_claims_without_a_token(client):
    assert client.token_claims() is None
