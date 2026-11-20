from . import PASSWORD
from . import USERNAME
from plone_client import PloneClient
from plone_client import tokens

import pytest
import time


pytestmark = pytest.mark.integration

# Longer than the 12 hours a plone.restapi token lasts, so any token is due.
ALWAYS = 13 * 3600


class Store:
    """A token store kept in memory."""

    def __init__(self, token: str) -> None:
        self.token = token
        self.saved: list[str] = []

    def load(self) -> str:
        return self.token

    def save(self, token: str) -> None:
        self.token = token
        self.saved.append(token)


def _token(plone_url: str) -> str:
    with PloneClient(plone_url, username=USERNAME, password=PASSWORD) as client:
        return client.post("/@login", {"login": USERNAME, "password": PASSWORD})[
            "token"
        ]


def _logged_in(client: PloneClient) -> bool:
    actions = client.navigation.actions(categories=["user"])
    return any(action.get("id") == "logout" for action in actions.get("user", []))


def test_token_is_renewed_and_saved(plone_url):
    token = _token(plone_url)
    # Two tokens issued in the same second are identical.
    time.sleep(1.1)
    store = Store(token)
    with PloneClient(
        plone_url, token=token, renew_margin=ALWAYS, token_store=store
    ) as client:
        assert _logged_in(client)
    (renewed,) = store.saved
    assert renewed != token
    assert tokens.subject(renewed) == USERNAME
    assert tokens.expires_at(renewed) > tokens.expires_at(token)
    with PloneClient(plone_url, token=renewed) as client:
        assert _logged_in(client)


def test_token_is_kept_outside_the_margin(plone_url):
    token = _token(plone_url)
    store = Store(token)
    with PloneClient(
        plone_url, token=token, renew_margin=60, token_store=store
    ) as client:
        assert _logged_in(client)
    assert store.saved == []
