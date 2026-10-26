"""``plone-client profile``: manage connection profiles and their secrets."""

from .. import credentials
from ..client import PloneClient
from ..exceptions import PloneAPIError
from ..exceptions import PloneConfigurationError
from ..profiles import AUTH_VALUES
from ..profiles import Profile
from ..profiles import SECRET_VALUES
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


@app.command("list")
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


@app.command()
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


@app.command()
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
    for, or read from standard input with --password-stdin.
    """
    state = get_state(ctx)
    profile = Profile(
        name=name,
        url=url,
        username=username,
        auth=auth,  # type: ignore[arg-type]
        secret=secret,  # type: ignore[arg-type]
        secret_env=secret_env,
        secret_command=secret_command,
        read_only=read_only,
        description=description,
    )
    config = state.config
    config.add(profile, replace=replace)
    if profile.secret == "keyring" and not profile.anonymous:
        label = "Token" if profile.auth == "token" else "Password"
        credentials.set_secret(profile, _read_secret(password_stdin, label))
    if use:
        config.current = name
    config.save()
    emit(ctx, {**profile.summary(), "current": config.current == name})


@app.command("set-secret")
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


@app.command()
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


@app.command()
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


@app.command()
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
