from .. import SITE_URL
from plone_client import PloneClient
from plone_client.cli import app
from plone_client.cli import state as state_module
from typer.testing import CliRunner
from typing import Any

import json
import pytest


@pytest.fixture
def cli_env(config_file, monkeypatch) -> dict[str, str]:
    """Environment of a command line run against the fake site, without profiles."""
    env = {
        "PLONE_CLIENT_URL": SITE_URL,
        "PLONE_CLIENT_USERNAME": "admin",
        "PLONE_CLIENT_PASSWORD": "secret",
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    return env


@pytest.fixture
def fake_transport(site, monkeypatch):
    """Make the command line's client talk to the fake site."""

    def factory(**kwargs: Any) -> PloneClient:
        return PloneClient(**kwargs, transport=site.transport, retries=0)

    monkeypatch.setattr(state_module, "PloneClient", factory)
    return site


class Run:
    """Result of a command line run."""

    def __init__(self, result) -> None:
        self.result = result
        self.exit_code = result.exit_code
        self.stdout = result.stdout
        self.stderr = result.stderr

    @property
    def json(self) -> Any:
        """Parsed standard output."""
        return json.loads(self.stdout)

    @property
    def error(self) -> Any:
        """Parsed standard error."""
        return json.loads(self.stderr)["error"]


@pytest.fixture
def invoke(fake_transport):
    """Run the command line."""
    runner = CliRunner()

    def func(*args: str, stdin: str | None = None) -> Run:
        return Run(runner.invoke(app, list(args), input=stdin))

    return func
