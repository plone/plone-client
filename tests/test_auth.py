from plone_client import auth
from plone_client.exceptions import PloneAuthenticationError

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
