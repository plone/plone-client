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
"""

from .exceptions import PloneConfigurationError
from typing import Any
from typing import TYPE_CHECKING

import os
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
