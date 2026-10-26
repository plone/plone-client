"""State shared by the commands: global options and the client."""

from ..client import PloneClient
from ..exceptions import PloneConfigurationError
from ..profiles import Config
from ..profiles import load_config
from ..profiles import Profile
from ..profiles import PROFILE_ENV
from ..profiles import settings_from_env
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any

import os
import typer


@dataclass
class State:
    """Global options of a command line run.

    :param profile: Profile name given with ``--profile``.
    :param url: Site URL given with ``--url``.
    :param username: Login name given with ``--username``.
    :param config_file: Configuration file given with ``--config``.
    :param read_only: Refuse changes to the site.
    :param dry_run: Show the changes instead of sending them.
    :param fields: Keys to keep in the output.
    :param compact: Print JSON on one line.
    """

    profile: str = ""
    url: str = ""
    username: str = ""
    config_file: Path | None = None
    read_only: bool = False
    dry_run: bool = False
    fields: list[str] = field(default_factory=list)
    compact: bool = False
    _client: PloneClient | None = None
    _config: Config | None = None

    @property
    def config(self) -> Config:
        """The configuration file, read once."""
        if self._config is None:
            self._config = load_config(self.config_file)
        return self._config

    def selected_profile(self) -> Profile | None:
        """Profile to connect with, or ``None`` to use the environment.

        :returns: The profile.
        :raises PloneConfigurationError: If no site is configured at all.
        """
        if self.profile:
            return self.config.get(self.profile)
        if self.url:
            return None
        if os.environ.get(PROFILE_ENV):
            return self.config.get(os.environ[PROFILE_ENV])
        if os.environ.get("PLONE_CLIENT_URL"):
            return None
        return self.config.get(self.config.current_name())

    def client_settings(self) -> dict[str, Any]:
        """Keyword arguments for the client.

        :returns: Settings from the profile, or from ``--url`` and the
            ``PLONE_CLIENT_*`` variables.
        """
        profile = self.selected_profile()
        if profile is not None:
            settings = profile.client_settings()
        else:
            environ = dict(os.environ)
            if self.url:
                environ["PLONE_CLIENT_URL"] = self.url
            settings = settings_from_env(environ)
        if self.username and profile is None:
            settings["username"] = self.username
        settings["read_only"] = settings.get("read_only", False) or self.read_only
        settings["dry_run"] = self.dry_run
        return settings

    @property
    def client(self) -> PloneClient:
        """The client, created on first use and closed at the end."""
        if self._client is None:
            self._client = PloneClient(**self.client_settings())
        return self._client

    def close(self) -> None:
        """Close the client, if one was created."""
        if self._client is not None:
            self._client.close()
            self._client = None


def get_state(ctx: typer.Context) -> State:
    """State of the current run.

    :param ctx: Typer context.
    :returns: The state set by the main callback.
    :raises PloneConfigurationError: If the callback did not run.
    """
    state = ctx.find_root().obj
    if not isinstance(state, State):  # no cov
        raise PloneConfigurationError("The command line state is missing")
    return state
