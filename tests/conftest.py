from . import FakeSite
from . import SITE_URL
from collections.abc import Generator
from plone_client import PloneClient
from typing import Any

import keyring
import keyring.backend
import keyring.errors
import pytest


@pytest.fixture
def site() -> FakeSite:
    """A fake Plone site."""
    return FakeSite()


@pytest.fixture
def client_factory(site: FakeSite):
    """Build clients that talk to the fake site."""

    def factory(**kwargs: Any) -> PloneClient:
        settings: dict[str, Any] = {
            "url": SITE_URL,
            "username": "admin",
            "password": "secret",
            "retries": 0,
            "backoff": 0,
            "transport": site.transport,
        }
        settings.update(kwargs)
        return PloneClient(**settings)

    return factory


@pytest.fixture
def client(client_factory) -> Generator[PloneClient]:
    """A client authenticated with basic auth."""
    with client_factory() as client:
        yield client


class MemoryKeyring(keyring.backend.KeyringBackend):
    """A keyring kept in memory."""

    priority = 1  # type: ignore[assignment]

    def __init__(self) -> None:
        super().__init__()
        self.store: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self.store.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self.store[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        try:
            del self.store[(service, username)]
        except KeyError:
            raise keyring.errors.PasswordDeleteError(username) from None


@pytest.fixture
def memory_keyring() -> Generator[MemoryKeyring]:
    """Replace the system keyring with one kept in memory."""
    previous = keyring.get_keyring()
    backend = MemoryKeyring()
    keyring.set_keyring(backend)
    yield backend
    keyring.set_keyring(previous)


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    """Path of an isolated configuration file, set in the environment."""
    path = tmp_path / "config" / "config.toml"
    monkeypatch.setenv("PLONE_CLIENT_CONFIG", str(path))
    for name in ("PLONE_CLIENT_PROFILE", "PLONE_CLIENT_URL", "PLONE_CLIENT_PASSWORD"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.chdir(tmp_path)
    return path
