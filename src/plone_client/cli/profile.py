"""``plone-client profile``: manage connection profiles and their secrets."""

from .. import credentials
from ..client import PloneClient
from ..exceptions import PloneAPIError
from ..exceptions import PloneConfigurationError
from ..profiles import AUTH_VALUES
from ..profiles import DEFAULT_KEYS
from ..profiles import parse_verify
from ..profiles import Profile
from ..profiles import SECRET_VALUES
from . import panels
from .output import emit
from .output import PloneGroup
from .state import get_state
from typing import Annotated
from typing import Any

import sys
import typer


app = typer.Typer(
    cls=PloneGroup,
    help="Manage connection profiles; secrets are kept in the system keyring.",
    no_args_is_help=True,
)


def _read_secret(from_stdin: bool, label: str) -> str:
    """Read a secret from standard input or from a hidden prompt.

    :param from_stdin: Read the first line of standard input.
    :param label: What is being asked for.
    :returns: The secret.
    :raises PloneConfigurationError: If it is empty.
    """
    if from_stdin:
        value = sys.stdin.readline().rstrip("\r\n")
    else:
        value = typer.prompt(label, hide_input=True)
    if not value:
        raise PloneConfigurationError(f"The {label.lower()} is empty")
    return str(value)


TIMEOUT_HELP = "Seconds to wait for the site."
VERIFY_HELP = "Verify TLS certificates: true, false, or a CA bundle path."
RETRIES_HELP = "Times a request is repeated after a network error."
BACKOFF_HELP = "Base delay in seconds between retries."


def _connection_settings(
    timeout: float | None,
    verify: str | None,
    retries: int | None,
    backoff: float | None,
) -> dict[str, Any]:
    """Connection settings given on the command line.

    :param timeout: ``--timeout``.
    :param verify: ``--verify``, as text.
    :param retries: ``--retries``.
    :param backoff: ``--backoff``.
    :returns: The settings that were given.
    """
    settings: dict[str, Any] = {
        "timeout": timeout,
        "verify": None if verify is None else parse_verify(verify),
        "retries": retries,
        "backoff": backoff,
    }
    return {key: value for key, value in settings.items() if value is not None}


def check_connection(client: PloneClient, username: str = "") -> dict[str, Any]:
    """Connect to a site and say who the client is logged in as.

    Plone answers requests with wrong credentials as anonymous ones, so the
    check looks for the ``logout`` action, which only authenticated users have.

    :param client: The client.
    :param username: Login name the client uses.
    :returns: URL, whether the client is authenticated, the user and, when
        visible, the Plone version.
    """
    actions = client.navigation.actions(categories=["user"])
    authenticated = any(
        action.get("id") == "logout" for action in actions.get("user", [])
    )
    result: dict[str, Any] = {
        "url": client.url,
        "authenticated": authenticated,
        "username": username if authenticated else None,
        "read_only": client.read_only,
    }
    try:
        result["plone_version"] = client.system.system().get("plone_version")
    except PloneAPIError:
        result["plone_version"] = None
    return result


@app.command("list", rich_help_panel=panels.BROWSE)
def list_profiles(ctx: typer.Context) -> None:
    """List the profiles; the current one is marked."""
    state = get_state(ctx)
    config = state.config
    current = config.current_name()
    emit(
        ctx,
        [
            {**profile.summary(), "current": name == current}
            for name, profile in sorted(config.profiles.items())
        ],
    )


@app.command(rich_help_panel=panels.BROWSE)
def show(
    ctx: typer.Context,
    name: Annotated[
        str, typer.Argument(help="Profile name; the current one by default.")
    ] = "",
) -> None:
    """Show the settings of a profile (never its secret)."""
    config = get_state(ctx).config
    profile = config.get(name or config.current_name())
    emit(ctx, {**profile.summary(), "config_file": str(config.path)})


@app.command(rich_help_panel=panels.WRITE)
def add(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Profile name.")],
    url: Annotated[str, typer.Option(help="URL of the site root.")],
    username: Annotated[
        str, typer.Option(help="Login name; empty for anonymous.")
    ] = "",
    auth: Annotated[
        str, typer.Option(help=f"One of {', '.join(AUTH_VALUES)}.")
    ] = "basic",
    secret: Annotated[
        str, typer.Option(help=f"Where the secret is: {', '.join(SECRET_VALUES)}.")
    ] = "keyring",
    secret_env: Annotated[
        str, typer.Option(help="Variable holding the secret, with --secret env.")
    ] = "PLONE_CLIENT_PASSWORD",
    secret_command: Annotated[
        str, typer.Option(help="Command printing the secret, with --secret command.")
    ] = "",
    read_only: Annotated[
        bool, typer.Option(help="Refuse changes to this site.")
    ] = False,
    timeout: Annotated[
        float | None, typer.Option(help=TIMEOUT_HELP, show_default=False)
    ] = None,
    verify: Annotated[
        str | None, typer.Option(help=VERIFY_HELP, show_default=False)
    ] = None,
    retries: Annotated[
        int | None, typer.Option(help=RETRIES_HELP, show_default=False)
    ] = None,
    backoff: Annotated[
        float | None, typer.Option(help=BACKOFF_HELP, show_default=False)
    ] = None,
    description: Annotated[str, typer.Option(help="Free text.")] = "",
    password_stdin: Annotated[
        bool,
        typer.Option("--password-stdin", help="Read the secret from standard input."),
    ] = False,
    use: Annotated[
        bool, typer.Option("--use", help="Make it the current profile.")
    ] = False,
    replace: Annotated[bool, typer.Option(help="Replace an existing profile.")] = False,
) -> None:
    """Add a profile, and store its secret in the keyring.

    With --secret keyring (the default) and a username, the password is asked
    for, or read from standard input with --password-stdin. Connection
    settings left out come from the defaults (see 'profile defaults').
    """
    state = get_state(ctx)
    config = state.config
    settings = _connection_settings(timeout, verify, retries, backoff)
    if read_only:
        settings["read_only"] = True
    profile = Profile(
        name=name,
        url=url,
        username=username,
        auth=auth,  # type: ignore[arg-type]
        secret=secret,  # type: ignore[arg-type]
        secret_env=secret_env,
        secret_command=secret_command,
        description=description,
        **{**config.defaults, **settings},
    )
    config.add(profile, replace=replace)
    if profile.secret == "keyring" and not profile.anonymous:
        label = "Token" if profile.auth == "token" else "Password"
        credentials.set_secret(profile, _read_secret(password_stdin, label))
    if use:
        config.current = name
    config.save()
    emit(ctx, {**profile.summary(), "current": config.current == name})


@app.command(rich_help_panel=panels.WRITE)
def defaults(
    ctx: typer.Context,
    timeout: Annotated[
        float | None, typer.Option(help=TIMEOUT_HELP, show_default=False)
    ] = None,
    verify: Annotated[
        str | None, typer.Option(help=VERIFY_HELP, show_default=False)
    ] = None,
    retries: Annotated[
        int | None, typer.Option(help=RETRIES_HELP, show_default=False)
    ] = None,
    backoff: Annotated[
        float | None, typer.Option(help=BACKOFF_HELP, show_default=False)
    ] = None,
    read_only: Annotated[
        bool | None,
        typer.Option(
            "--read-only/--read-write",
            help="Refuse changes to every site.",
            show_default=False,
        ),
    ] = None,
    unset: Annotated[
        list[str] | None,
        typer.Option(help=f"Remove a setting: {', '.join(DEFAULT_KEYS)}."),
    ] = None,
) -> None:
    """Show or change the connection settings shared by every profile.

    Without options, show them. A profile's own setting wins over these.
    """
    config = get_state(ctx).config
    values: dict[str, Any] = _connection_settings(timeout, verify, retries, backoff)
    if read_only is not None:
        values["read_only"] = read_only
    for key in unset or []:
        values[key.replace("-", "_")] = None
    if values:
        config.set_defaults(values)
        config.save()
    emit(ctx, {"defaults": config.defaults, "config_file": str(config.path)})


@app.command("set-secret", rich_help_panel=panels.CONNECTION)
def set_secret(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Profile name.")],
    password_stdin: Annotated[
        bool,
        typer.Option("--password-stdin", help="Read the secret from standard input."),
    ] = False,
) -> None:
    """Store or replace the secret of a profile in the keyring."""
    profile = get_state(ctx).config.get(name)
    label = "Token" if profile.auth == "token" else "Password"
    credentials.set_secret(profile, _read_secret(password_stdin, label))
    emit(ctx, {"name": name, "secret": "stored"})


@app.command(rich_help_panel=panels.WRITE)
def use(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Profile name.")],
) -> None:
    """Make a profile the current one."""
    config = get_state(ctx).config
    config.get(name)
    config.current = name
    config.save()
    emit(ctx, {"current": name})


@app.command(rich_help_panel=panels.WRITE)
def remove(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Profile name.")],
    keep_secret: Annotated[
        bool, typer.Option(help="Leave the secret in the keyring.")
    ] = False,
) -> None:
    """Remove a profile and its secret."""
    config = get_state(ctx).config
    profile = config.remove(name)
    removed_secret = False if keep_secret else credentials.delete_secret(profile)
    config.save()
    emit(ctx, {"removed": name, "secret_removed": removed_secret})


@app.command(rich_help_panel=panels.CONNECTION)
def test(
    ctx: typer.Context,
    name: Annotated[
        str, typer.Argument(help="Profile name; the current one by default.")
    ] = "",
) -> None:
    """Connect with a profile and report who the client is logged in as."""
    state = get_state(ctx)
    profile = state.config.get(name or state.config.current_name())
    state.profile = profile.name
    result = check_connection(state.client, profile.username)
    emit(ctx, {"profile": profile.name, **result})
