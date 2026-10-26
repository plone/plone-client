"""Named connection profiles, so one machine can talk to many sites.

A profile names a site, a user and where that user's secret is kept. The
profiles live in a TOML file, by default ``~/.config/plone-client/config.toml``
(``$XDG_CONFIG_HOME`` and ``$PLONE_CLIENT_CONFIG`` are honored)::

    current = "blog"

    [profiles.blog]
    url = "https://example.org"
    username = "editor"

    [profiles.local]
    url = "http://localhost:8080/Plone"
    username = "admin"
    auth = "jwt"

    [profiles.production]
    url = "https://www.example.com"
    username = "editor"
    read_only = true
    secret = "command"
    secret_command = "op read op://Private/example/password"

Secrets never go in the file. By default they are kept in the operating
system's keyring (macOS Keychain, Windows Credential Locker, Secret Service
on Linux); see :mod:`plone_client.credentials` for the other sources.

Which profile is used, from the strongest choice to the weakest: the name
passed explicitly, ``$PLONE_CLIENT_PROFILE``, a ``.plone-client.toml`` file
in the working directory or one of its parents (``profile = "blog"``), and
the ``current`` profile of the configuration file.
"""

from .exceptions import PloneConfigurationError
from collections.abc import Mapping
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import fields
from pathlib import Path
from typing import Any
from typing import Literal

import os
import re
import tomllib


CONFIG_ENV = "PLONE_CLIENT_CONFIG"
PROFILE_ENV = "PLONE_CLIENT_PROFILE"
PROJECT_FILE = ".plone-client.toml"
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

Auth = Literal["basic", "jwt", "token"]
SecretSource = Literal["keyring", "env", "command", "none"]
AUTH_VALUES: tuple[str, ...] = ("basic", "jwt", "token")
SECRET_VALUES: tuple[str, ...] = ("keyring", "env", "command", "none")


def default_config_path(environ: Mapping[str, str] | None = None) -> Path:
    """Path of the user's configuration file.

    :param environ: Environment; ``os.environ`` by default.
    :returns: ``$PLONE_CLIENT_CONFIG``, or ``config.toml`` inside
        ``$XDG_CONFIG_HOME/plone-client`` (``~/.config/plone-client``).
    """
    environ = os.environ if environ is None else environ
    if environ.get(CONFIG_ENV):
        return Path(environ[CONFIG_ENV]).expanduser()
    base = environ.get("XDG_CONFIG_HOME") or "~/.config"
    return Path(base).expanduser() / "plone-client" / "config.toml"


def find_project_profile(start: Path | None = None) -> str:
    """Profile named by a ``.plone-client.toml`` file.

    The file is looked for in ``start`` and in each of its parents, so a
    repository can say which site it works with. It holds no secrets and can
    be committed.

    :param start: Directory to start from; the working directory by default.
    :returns: The profile name, or an empty string when there is no file.
    """
    directory = (start or Path.cwd()).resolve()
    for candidate in (directory, *directory.parents):
        path = candidate / PROJECT_FILE
        if path.is_file():
            data = tomllib.loads(path.read_text())
            return str(data.get("profile", ""))
    return ""


@dataclass
class Profile:
    """Connection settings of one site.

    :param name: Profile name.
    :param url: URL of the site root.
    :param username: Login name; empty for anonymous access.
    :param auth: ``basic`` or ``jwt`` with a username and password, or
        ``token`` to send the secret as a JWT.
    :param secret: Where the secret is kept: ``keyring``, ``env``,
        ``command`` or ``none``.
    :param secret_env: Variable holding the secret, with ``secret = "env"``.
    :param secret_command: Command printing the secret, with
        ``secret = "command"``; run without a shell.
    :param read_only: Refuse every request that could change the site.
    :param timeout: Seconds to wait for the site.
    :param verify: Verify TLS certificates.
    :param api_prefix: Traversal prefix of the REST API.
    :param description: Free text, shown by ``plone-client profile list``.
    """

    name: str
    url: str
    username: str = ""
    auth: Auth = "basic"
    secret: SecretSource = "keyring"
    secret_env: str = "PLONE_CLIENT_PASSWORD"
    secret_command: str = ""
    read_only: bool = False
    timeout: float = 30.0
    verify: bool = True
    api_prefix: str = "++api++"
    description: str = ""

    def __post_init__(self) -> None:
        if not NAME_RE.match(self.name):
            raise PloneConfigurationError(f"Invalid profile name: {self.name!r}")
        if not self.url:
            raise PloneConfigurationError(f"Profile {self.name!r} has no url")
        if self.auth not in AUTH_VALUES:
            raise PloneConfigurationError(
                f"Profile {self.name!r}: auth must be one of {', '.join(AUTH_VALUES)}"
            )
        if self.secret not in SECRET_VALUES:
            raise PloneConfigurationError(
                f"Profile {self.name!r}: secret must be one of "
                f"{', '.join(SECRET_VALUES)}"
            )
        if self.secret == "command" and not self.secret_command:
            raise PloneConfigurationError(
                f"Profile {self.name!r}: secret_command is required"
            )
        self.url = self.url.rstrip("/")

    @property
    def anonymous(self) -> bool:
        """Whether requests go out without credentials."""
        return self.secret == "none" or (self.auth != "token" and not self.username)

    @classmethod
    def from_mapping(cls, name: str, data: Mapping[str, Any]) -> "Profile":
        """Build a profile from a table of the configuration file.

        :param name: Profile name.
        :param data: The table.
        :returns: The profile.
        :raises PloneConfigurationError: If a key is unknown or a value invalid.
        """
        known = {f.name for f in fields(cls)} - {"name"}
        unknown = set(data) - known
        if unknown:
            raise PloneConfigurationError(
                f"Profile {name!r}: unknown keys {', '.join(sorted(unknown))}"
            )
        return cls(name=name, **dict(data))

    def to_mapping(self) -> dict[str, Any]:
        """Table for the configuration file, without default values.

        :returns: The settings that differ from the defaults, ``url`` first.
        """
        defaults = Profile(name=self.name, url=self.url)
        return {
            key: value
            for key, value in asdict(self).items()
            if key != "name" and (key == "url" or value != getattr(defaults, key))
        }

    def get_secret(self) -> str:
        """The profile's password or token.

        :returns: The secret, or an empty string for anonymous profiles.
        :raises PloneConfigurationError: If the secret cannot be found.
        """
        from .credentials import get_secret

        return "" if self.anonymous else get_secret(self)

    def client_settings(self) -> dict[str, Any]:
        """Keyword arguments for :class:`~plone_client.PloneClient`.

        :returns: URL, credentials and options; the secret is looked up now.
        """
        settings: dict[str, Any] = {
            "url": self.url,
            "api_prefix": self.api_prefix,
            "timeout": self.timeout,
            "verify": self.verify,
            "read_only": self.read_only,
        }
        secret = self.get_secret()
        if self.auth == "token":
            settings["token"] = secret
        elif not self.anonymous:
            settings.update(
                username=self.username, password=secret, auth_method=self.auth
            )
        return settings

    def summary(self) -> dict[str, Any]:
        """Description of the profile, safe to print.

        :returns: Settings without any secret.
        """
        return {"name": self.name, **self.to_mapping()}


class Config:
    """The profiles of a configuration file.

    :param path: Path of the file.
    :param data: Parsed contents.
    """

    def __init__(self, path: Path, data: Mapping[str, Any] | None = None) -> None:
        self.path = path
        data = dict(data or {})
        self.current: str = str(data.get("current", ""))
        self.profiles: dict[str, Profile] = {
            name: Profile.from_mapping(name, table)
            for name, table in (data.get("profiles") or {}).items()
        }

    def get(self, name: str) -> Profile:
        """A profile by name.

        :param name: Profile name.
        :returns: The profile.
        :raises PloneConfigurationError: If there is no such profile.
        """
        if not name:
            raise PloneConfigurationError(
                "No profile selected: pass one, set $PLONE_CLIENT_PROFILE, "
                f"add a {PROJECT_FILE} file or run 'plone-client profile use'"
            )
        try:
            return self.profiles[name]
        except KeyError:
            known = ", ".join(sorted(self.profiles)) or "none"
            raise PloneConfigurationError(
                f"Unknown profile {name!r} in {self.path} (known: {known})"
            ) from None

    def current_name(
        self,
        environ: Mapping[str, str] | None = None,
        cwd: Path | None = None,
    ) -> str:
        """Name of the profile to use when none is given explicitly.

        :param environ: Environment; ``os.environ`` by default.
        :param cwd: Directory where ``.plone-client.toml`` is looked for.
        :returns: The name, or an empty string.
        """
        environ = os.environ if environ is None else environ
        return environ.get(PROFILE_ENV) or find_project_profile(cwd) or self.current

    def add(self, profile: Profile, *, replace: bool = False) -> None:
        """Add a profile.

        :param profile: The profile.
        :param replace: Replace a profile with the same name.
        :raises PloneConfigurationError: If the name is taken.
        """
        if profile.name in self.profiles and not replace:
            raise PloneConfigurationError(f"Profile {profile.name!r} already exists")
        self.profiles[profile.name] = profile
        if not self.current:
            self.current = profile.name

    def remove(self, name: str) -> Profile:
        """Remove a profile.

        :param name: Profile name.
        :returns: The removed profile.
        """
        profile = self.get(name)
        del self.profiles[name]
        if self.current == name:
            self.current = ""
        return profile

    def to_mapping(self) -> dict[str, Any]:
        """Contents of the configuration file.

        :returns: ``current`` and the ``profiles`` tables.
        """
        data: dict[str, Any] = {}
        if self.current:
            data["current"] = self.current
        data["profiles"] = {
            name: profile.to_mapping()
            for name, profile in sorted(self.profiles.items())
        }
        return data

    def save(self) -> None:
        """Write the configuration file, readable only by its owner.

        :raises PloneConfigurationError: If ``tomlkit`` is not installed.
        """
        try:
            import tomlkit
        except ImportError:  # no cov
            raise PloneConfigurationError(
                "Saving profiles needs the 'cli' extra: pip install 'plone-client[cli]'"
            ) from None
        self.path.parent.mkdir(parents=True, exist_ok=True)
        text = tomlkit.dumps(self.to_mapping())
        self.path.write_text(text)
        self.path.chmod(0o600)


def load_config(path: Path | None = None) -> Config:
    """Read a configuration file.

    :param path: Path of the file; the user's by default. A missing file
        gives an empty configuration.
    :returns: The configuration.
    :raises PloneConfigurationError: If the file is not valid.
    """
    path = path or default_config_path()
    if not path.exists():
        return Config(path)
    try:
        data = tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as exc:
        raise PloneConfigurationError(f"{path}: {exc}") from exc
    return Config(path, data)


def _bool(value: str) -> bool:
    """Read a boolean environment variable.

    :param value: The value.
    :returns: ``False`` for ``0``, ``false``, ``no`` and ``off``.
    """
    return value.strip().lower() not in {"0", "false", "no", "off", ""}


def settings_from_env(
    environ: Mapping[str, str], *, prefix: str = "PLONE_CLIENT_"
) -> dict[str, Any]:
    """Client settings from environment variables.

    Reads ``URL``, ``USERNAME`` (or ``USER``), ``PASSWORD``, ``TOKEN``,
    ``AUTH_METHOD``, ``API_PREFIX``, ``TIMEOUT``, ``VERIFY`` and
    ``READ_ONLY``, each after the prefix. With ``prefix="REMOTE_"``, this
    reads the ``REMOTE_URL``, ``REMOTE_USER`` and ``REMOTE_PASSWORD``
    variables used by older scripts.

    :param environ: The environment.
    :param prefix: Prefix of the variable names.
    :returns: Keyword arguments for :class:`~plone_client.PloneClient`.
    :raises PloneConfigurationError: If the URL is not set.
    """

    def value(name: str) -> str:
        return environ.get(f"{prefix}{name}", "").strip()

    url = value("URL")
    if not url:
        raise PloneConfigurationError(f"Set {prefix}URL to the URL of the site")
    settings: dict[str, Any] = {
        "url": url,
        "username": value("USERNAME") or value("USER"),
        "password": environ.get(f"{prefix}PASSWORD", ""),
        "token": value("TOKEN"),
    }
    if value("AUTH_METHOD"):
        settings["auth_method"] = value("AUTH_METHOD")
    if f"{prefix}API_PREFIX" in environ:
        settings["api_prefix"] = value("API_PREFIX")
    if value("TIMEOUT"):
        try:
            settings["timeout"] = float(value("TIMEOUT"))
        except ValueError:
            raise PloneConfigurationError(f"{prefix}TIMEOUT must be a number") from None
    if value("VERIFY"):
        settings["verify"] = _bool(value("VERIFY"))
    if value("READ_ONLY"):
        settings["read_only"] = _bool(value("READ_ONLY"))
    return settings
