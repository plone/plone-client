"""What a JSON Web Token says about itself, and where a renewed one is kept.

``plone.restapi`` issues JWTs that expire, 12 hours after they were issued
by default. The client reads the token's ``exp`` claim to renew it in time
(see :class:`~plone_client.auth.TokenAuth`). The claims are read without
checking the signature: plone-client cannot check it, and does not need to,
since the site checks the token on every request. They are only used to
decide when to renew and to say who the token belongs to.
"""

from collections.abc import Mapping
from datetime import datetime
from datetime import UTC
from typing import Any
from typing import Protocol

import base64
import binascii
import json


class TokenStore(Protocol):
    """Where a token is kept between runs, such as a profile's keyring entry.

    :class:`~plone_client.auth.TokenAuth` loads the token from the store
    before renewing it, in case another process renewed it first, and saves
    the token it renewed.
    """

    def load(self) -> str:
        """The token kept in the store.

        :returns: The token, or an empty string when there is none.
        """

    def save(self, token: str) -> None:
        """Keep a token in the store, replacing the previous one.

        :param token: The token.
        """


def claims(token: str) -> dict[str, Any] | None:
    """The claims of a JWT, read without checking its signature.

    :param token: The token.
    :returns: The payload, or ``None`` when the token is not a JWT with a
        JSON object as its payload (an opaque token, for instance).
    """
    parts = token.split(".")
    if len(parts) != 3 or not parts[1]:
        return None
    segment = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        payload = json.loads(base64.urlsafe_b64decode(segment))
    except (binascii.Error, ValueError):  # JSONDecodeError and UnicodeDecodeError
        return None
    return payload if isinstance(payload, dict) else None


def expires_at(token: str) -> datetime | None:
    """When a JWT expires.

    :param token: The token.
    :returns: The ``exp`` claim, in UTC, or ``None`` when the token has none.
    """
    return expiry(claims(token) or {})


def expiry(payload: Mapping[str, Any]) -> datetime | None:
    """The ``exp`` claim of a token's claims, as a time.

    :param payload: The claims, from :func:`claims`.
    :returns: The time, in UTC, or ``None`` when there is no valid ``exp``.
    """
    value = payload.get("exp")
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    try:
        return datetime.fromtimestamp(value, tz=UTC)
    except (OverflowError, OSError, ValueError):
        return None


def subject(token: str) -> str | None:
    """Who a JWT was issued to.

    :param token: The token.
    :returns: The ``sub`` claim (the Plone user id), or ``None``.
    """
    value = (claims(token) or {}).get("sub")
    return value if isinstance(value, str) and value else None
