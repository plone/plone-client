"""Where the password or token of a profile is kept.

``keyring`` (default)
    The operating system's secret store, through the :mod:`keyring` package:
    macOS Keychain, Windows Credential Locker, or the Secret Service on Linux.
    Entries are stored under the service ``plone-client:<profile>``.
``env``
    An environment variable, named by the profile's ``secret_env``
    (``PLONE_CLIENT_PASSWORD`` by default). Handy in CI.
``command``
    The output of a command, named by the profile's ``secret_command``, such
    as ``op read op://Private/site/password`` or ``pass show plone/site``.
    The command runs without a shell.
``none``
    No secret: the profile is anonymous.

The token that MCP clients send to ``plone-client mcp --http`` is kept in the
keyring too, under the service ``plone-client`` (no profile has that
service), or in ``$PLONE_CLIENT_MCP_TOKEN``, which wins.
"""

from .exceptions import PloneConfigurationError
from typing import Any
from typing import TYPE_CHECKING

import os
import secrets
import shlex
import subprocess


if TYPE_CHECKING:
    from .profiles import Profile


SERVICE_PREFIX = "plone-client"


def keyring_service(profile: "Profile") -> str:
    """Keyring service name of a profile.

    :param profile: The profile.
    :returns: ``plone-client:<profile name>``.
    """
    return f"{SERVICE_PREFIX}:{profile.name}"


def keyring_account(profile: "Profile") -> str:
    """Keyring account name of a profile.

    :param profile: The profile.
    :returns: The username, or ``token`` for token profiles without one.
    """
    return profile.username or "token"


def _keyring() -> Any:
    """Import :mod:`keyring`.

    :returns: The module.
    :raises PloneConfigurationError: If it is not installed.
    """
    try:
        import keyring
    except ImportError:  # no cov
        raise PloneConfigurationError(
            "The keyring needs the 'cli' extra: pip install 'plone-client[cli]'"
        ) from None
    return keyring


def get_secret(profile: "Profile") -> str:
    """Look up the secret of a profile.

    :param profile: The profile.
    :returns: The password or token.
    :raises PloneConfigurationError: If the secret is missing.
    """
    if profile.secret == "none":
        return ""
    if profile.secret == "env":
        value = os.environ.get(profile.secret_env, "")
        if not value:
            raise PloneConfigurationError(
                f"Profile {profile.name!r}: set ${profile.secret_env}"
            )
        return value
    if profile.secret == "command":
        return _run_command(profile)
    value = _keyring().get_password(keyring_service(profile), keyring_account(profile))
    if not value:
        raise PloneConfigurationError(
            f"Profile {profile.name!r}: no secret in the keyring; "
            f"run 'plone-client profile set-secret {profile.name}'"
        )
    return str(value)


def _run_command(profile: "Profile") -> str:
    """Run the secret command of a profile.

    :param profile: The profile.
    :returns: The first line of the command's output.
    :raises PloneConfigurationError: If the command fails or prints nothing.
    """
    try:
        result = subprocess.run(  # noqa: S603
            shlex.split(profile.secret_command),
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PloneConfigurationError(
            f"Profile {profile.name!r}: secret command failed: {exc}"
        ) from exc
    value = result.stdout.splitlines()[0].strip() if result.stdout else ""
    if result.returncode or not value:
        raise PloneConfigurationError(
            f"Profile {profile.name!r}: secret command exited with "
            f"{result.returncode} and printed no secret"
        )
    return value


def set_secret(profile: "Profile", value: str) -> None:
    """Store the secret of a profile in the keyring.

    :param profile: The profile.
    :param value: The password or token.
    :raises PloneConfigurationError: If the profile keeps its secret elsewhere.
    """
    if profile.secret != "keyring":
        raise PloneConfigurationError(
            f"Profile {profile.name!r} reads its secret from {profile.secret!r}, "
            "not from the keyring"
        )
    _keyring().set_password(keyring_service(profile), keyring_account(profile), value)


def delete_secret(profile: "Profile") -> bool:
    """Remove the secret of a profile from the keyring.

    :param profile: The profile.
    :returns: ``True`` if there was a secret to remove.
    """
    if profile.secret != "keyring":
        return False
    keyring = _keyring()
    try:
        keyring.delete_password(keyring_service(profile), keyring_account(profile))
    except keyring.errors.PasswordDeleteError:
        return False
    return True


#: Environment variable with the token of the MCP server; wins over the keyring.
MCP_TOKEN_ENV = "PLONE_CLIENT_MCP_TOKEN"
#: Keyring account of the MCP server's token, under the service ``plone-client``.
MCP_TOKEN_ACCOUNT = "mcp-token"
#: Shortest token the MCP server accepts.
MCP_TOKEN_MIN_LENGTH = 32


def _check_mcp_token(value: str, origin: str) -> str:
    """Refuse a token too short to resist guessing.

    :param value: The token.
    :param origin: Where it came from, for the message.
    :returns: The token.
    :raises PloneConfigurationError: If it is shorter than
        :data:`MCP_TOKEN_MIN_LENGTH`.
    """
    if len(value) < MCP_TOKEN_MIN_LENGTH:
        raise PloneConfigurationError(
            f"The MCP token {origin} has {len(value)} characters; it needs at "
            f"least {MCP_TOKEN_MIN_LENGTH}. Run 'plone-client mcp-token generate'"
        )
    return value


def get_mcp_token() -> str:
    """The token that MCP clients must send to the HTTP server.

    :returns: ``$PLONE_CLIENT_MCP_TOKEN`` when set, or the token in the keyring.
    :raises PloneConfigurationError: If there is none, or it is too short.
    """
    value = os.environ.get(MCP_TOKEN_ENV, "")
    if value:
        return _check_mcp_token(value, f"in ${MCP_TOKEN_ENV}")
    value = _keyring().get_password(SERVICE_PREFIX, MCP_TOKEN_ACCOUNT) or ""
    if not value:
        raise PloneConfigurationError(
            "The MCP server over HTTP needs a token: run "
            f"'plone-client mcp-token generate', or set ${MCP_TOKEN_ENV}"
        )
    return _check_mcp_token(str(value), "in the keyring")


def set_mcp_token(value: str) -> None:
    """Store the token of the MCP server in the keyring.

    :param value: The token.
    :raises PloneConfigurationError: If it is too short.
    """
    _check_mcp_token(value, "given")
    _keyring().set_password(SERVICE_PREFIX, MCP_TOKEN_ACCOUNT, value)


def generate_mcp_token() -> str:
    """Make a new random token for the MCP server and store it in the keyring.

    :returns: The token, for the MCP clients' configuration.
    """
    value = secrets.token_urlsafe(32)
    set_mcp_token(value)
    return value


def delete_mcp_token() -> bool:
    """Remove the token of the MCP server from the keyring.

    :returns: ``True`` if there was a token to remove.
    """
    keyring = _keyring()
    try:
        keyring.delete_password(SERVICE_PREFIX, MCP_TOKEN_ACCOUNT)
    except keyring.errors.PasswordDeleteError:
        return False
    return True
