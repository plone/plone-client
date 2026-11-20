from . import make_jwt
from datetime import datetime
from datetime import UTC
from plone_client import tokens

import base64
import pytest


def _token(payload: bytes) -> str:
    """A token whose payload segment holds these bytes."""
    segment = base64.urlsafe_b64encode(payload).decode().rstrip("=")
    return f"header.{segment}.signature"


def test_claims_of_a_jwt():
    token = make_jwt(sub="editor", exp=1_800_000_000, fullname="Ed Itor")
    assert tokens.claims(token) == {
        "sub": "editor",
        "exp": 1_800_000_000,
        "fullname": "Ed Itor",
    }


@pytest.mark.parametrize("length", [1, 2, 3, 4, 5])
def test_claims_restore_the_padding(length):
    # Payloads of every length mod 4 need different padding.
    token = make_jwt(sub="x" * length)
    assert tokens.claims(token) == {"sub": "x" * length}


@pytest.mark.parametrize(
    "token",
    [
        "",
        "opaque-personal-access-token",
        "two.parts",
        "four.parts.in.it",
        "header..signature",
        "header.!!!.signature",
        _token(b"not json"),
        _token(b"[1, 2]"),
        _token(b"\xff\xfe"),
    ],
)
def test_claims_of_something_else(token):
    assert tokens.claims(token) is None


def test_expires_at():
    token = make_jwt(exp=1_800_000_000)
    assert tokens.expires_at(token) == datetime.fromtimestamp(1_800_000_000, tz=UTC)


@pytest.mark.parametrize(
    "payload",
    [{}, {"exp": "tomorrow"}, {"exp": True}, {"exp": 10**20}],
)
def test_expires_at_without_a_valid_exp(payload):
    assert tokens.expires_at(make_jwt(**payload)) is None


def test_expires_at_of_an_opaque_token():
    assert tokens.expires_at("opaque") is None


@pytest.mark.parametrize(
    "payload,expected",
    [
        ({"sub": "editor"}, "editor"),
        ({}, None),
        ({"sub": ""}, None),
        ({"sub": 1}, None),
    ],
)
def test_subject(payload, expected):
    assert tokens.subject(make_jwt(**payload)) == expected
