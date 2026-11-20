"""``plone-client profile``: manage connection profiles and their secrets."""

from .. import credentials
from ..client import PloneClient
from ..exceptions import PloneAPIError
from ..exceptions import PloneConfigurationError
from ..profiles import AUTH_VALUES
from ..profiles import Config
from ..profiles import DEFAULT_KEYS
from ..profiles import parse_verify
from ..profiles import Profile
from ..profiles import SECRET_VALUES
from ..tokens import expiry
from . import panels
from .output import emit
from .output import parse_assignments
from .output import parse_value
from .output import PloneGroup
from .state import get_state
from dataclasses import fields
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
    Credentials are rejected when the client has a username or a token and
    the site still answers as anonymous; without any, anonymous is expected.

    A client with a JWT also reports when the token expires and whom it was
    issued to; the user is taken from the token when no username is set.

    :param client: The client.
    :param username: Login name the client uses.
    :returns: URL, whether the client is authenticated, the user, the
        token's expiry and subject (for a JWT), whether the credentials were
        rejected and, when visible, the Plone version.
    """
    actions = client.navigation.actions(categories=["user"])
    authenticated = any(
        action.get("id") == "logout" for action in actions.get("user", [])
    )
    token = client.token_claims()
    subject = token.get("sub") if token else None
    subject = subject if isinstance(subject, str) and subject else None
    result: dict[str, Any] = {
        "url": client.url,
        "authenticated": authenticated,
        "username": (username or subject) if authenticated else None,
    }
    if token is not None:
        expires = expiry(token)
        result["token_expires"] = expires.isoformat() if expires else None
        result["token_subject"] = subject
    result["credentials_rejected"] = client.has_credentials and not authenticated
    result["read_only"] = client.read_only
    try:
        result["plone_version"] = client.system.system().get("plone_version")
    except PloneAPIError:
        result["plone_version"] = None
    return result


def rejected_message(profile: str) -> str:
    """Message for a profile whose credentials the site rejected.

    :param profile: Name of the profile, as ``profile set-secret`` takes it.
    :returns: The message, with the command that fixes the secret.
    """
    return (
        f"Credentials were rejected: profile {profile!r} has a username or a "
        "token, but the site answers as anonymous. Fix the secret with: "
        f"plone-client profile set-secret {profile}"
    )


def emit_connection(ctx: typer.Context, payload: dict[str, Any], profile: str) -> None:
    """Print a connection report, and exit with code 4 if credentials were rejected.

    :param ctx: Typer context.
    :param payload: The report, from :func:`check_connection`.
    :param profile: Name of the profile to show in the message.
    :raises typer.Exit: With code 4 (not authenticated) when the credentials
        were rejected; the report is printed first.
    """
    if not payload["credentials_rejected"]:
        emit(ctx, payload)
        return
    emit(ctx, {**payload, "message": rejected_message(profile)})
    raise typer.Exit(4)


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
    transition: Annotated[
        list[str] | None,
        typer.Option(
            help="The only workflow transition run on this site; repeat it to "
            "allow more. Without it, every transition runs.",
            show_default=False,
        ),
    ] = None,
    plate_type: Annotated[
        list[str] | None,
        typer.Option(
            help="A content type whose pages are one Plate document, for sites "
            "whose Volto does not say so; repeat it for more types.",
            show_default=False,
        ),
    ] = None,
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
    renew_margin: Annotated[
        float | None,
        typer.Option(
            help="With --auth token, renew the token when it expires within "
            "these seconds (3600 by default); 0 never renews it.",
            show_default=False,
        ),
    ] = None,
    frontend_url: Annotated[
        str,
        typer.Option(
            help="URL of the Volto frontend, when --url is the backend; "
            "used to list the site's blocks."
        ),
    ] = "",
    blocks_setting: Annotated[
        str | None,
        typer.Option(
            "--blocks",
            help="Block types that Markdown and HTML become on this site, as "
            "JSON, such as '{\"codeBlock\": true}'.",
        ),
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
    if renew_margin is not None:
        settings["renew_margin"] = renew_margin
    if transition:
        settings["transitions"] = list(transition)
    if plate_type:
        settings["plate_types"] = list(plate_type)
    if blocks_setting is not None:
        settings["blocks"] = parse_value(blocks_setting)
    profile = Profile(
        name=name,
        url=url,
        username=username,
        auth=auth,  # type: ignore[arg-type]
        secret=secret,  # type: ignore[arg-type]
        secret_env=secret_env,
        secret_command=secret_command,
        frontend_url=frontend_url,
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


#: Settings that ``profile set`` and ``profile unset`` never change: the name,
#: and how the secret is read, which the keyring entry depends on.
PROTECTED_SETTINGS: dict[str, str] = {
    "name": "The name of a profile cannot be changed; add the profile again "
    "under the new name.",
    "auth": "Changing the auth changes what the stored secret is; use "
    "'profile add --replace' for that.",
    "secret": "Changing where the secret is kept leaves the keyring entry "
    "behind; use 'profile add --replace' for that.",
}


def _setting_key(key: str) -> str:
    """Setting name as the configuration file spells it.

    :param key: The name as typed, with ``-`` or ``_``.
    :returns: The name with underscores.
    """
    return key.replace("-", "_")


def _check_setting_keys(name: str, keys: list[str], refused: dict[str, str]) -> None:
    """Refuse the settings that cannot be changed this way, or do not exist.

    :param name: Profile name, for the messages.
    :param keys: Setting names, with underscores.
    :param refused: Setting names that are refused, with the reason.
    :raises PloneConfigurationError: If a key is refused or unknown.
    """
    for key in keys:
        if key in refused:
            raise PloneConfigurationError(f"Profile {name!r}: {refused[key]}")
    known = {f.name for f in fields(Profile)}
    unknown = sorted(set(keys) - known)
    if unknown:
        raise PloneConfigurationError(
            f"Profile {name!r}: unknown keys {', '.join(unknown)}"
        )


def _check_setting_type(name: str, key: str, value: Any, baseline: Profile) -> None:
    """Refuse a value of the wrong kind for its setting.

    :param name: Profile name, for the message.
    :param key: Setting name.
    :param value: The new value.
    :param baseline: A profile with the class defaults, for the kind.
    :raises PloneConfigurationError: If the value is of another kind.
    """
    default = getattr(baseline, key)
    if key == "verify":
        valid = isinstance(value, bool | str)
        kind = "true, false or a CA bundle path"
    elif isinstance(default, bool):
        valid = isinstance(value, bool)
        kind = "true or false"
    elif isinstance(default, int | float):
        valid = isinstance(value, int | float) and not isinstance(value, bool)
        kind = "a number"
    elif isinstance(default, str):
        valid = isinstance(value, str)
        kind = "a string"
    else:
        valid = isinstance(value, type(default))
        kind = f"a JSON {type(default).__name__}"
    if not valid:
        raise PloneConfigurationError(f"Profile {name!r}: {key} must be {kind}")


def _changed_profile(
    config: Config,
    name: str,
    values: dict[str, Any],
    unset: list[str] | None = None,
) -> Profile:
    """The profile with some settings changed, checked as any profile is.

    Settings the profile takes from the defaults stay out of its own table.
    Nothing is written here: the caller saves the configuration when this
    returns.

    :param config: The configuration.
    :param name: Profile name.
    :param values: Settings to set.
    :param unset: Settings to remove, so that they return to the defaults.
    :returns: The new profile.
    :raises PloneConfigurationError: If a setting is refused, unknown, of the
        wrong kind, or its value is invalid.
    """
    profile = config.get(name)
    baseline = Profile(name=name, url=profile.url)
    own = profile.to_mapping(config.defaults)
    for key in unset or []:
        own.pop(key, None)
    for key, value in values.items():
        _check_setting_type(name, key, value, baseline)
    own.update(values)
    return Profile.from_mapping(name, {**config.defaults, **own})


@app.command("set", rich_help_panel=panels.WRITE)
def set_settings(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Profile name.")],
    assignments: Annotated[
        list[str],
        typer.Argument(
            metavar="KEY=VALUE...",
            help="key=text for a string, key:=json for any other value, such as "
            "'plate_types:=[\"WikiPage\"]' or 'read_only:=true'.",
        ),
    ],
) -> None:
    """Change some settings of a profile; the others, and its secret, stay.

    The new profile is checked like any profile before the configuration file
    is written: an unknown key, a value of the wrong kind or an invalid value
    is refused, and the file stays as it was.
    """
    config = get_state(ctx).config
    try:
        parsed = parse_assignments(assignments)
    except ValueError as error:
        raise PloneConfigurationError(str(error)) from None
    values = {_setting_key(key): value for key, value in parsed.items()}
    _check_setting_keys(name, list(values), PROTECTED_SETTINGS)
    profile = _changed_profile(config, name, values)
    config.add(profile, replace=True)
    config.save()
    emit(ctx, {**profile.summary(), "changed": sorted(values)})


@app.command("unset", rich_help_panel=panels.WRITE)
def unset_settings(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Profile name.")],
    keys: Annotated[
        list[str],
        typer.Argument(
            metavar="KEY...",
            help="Settings to remove; each returns to the defaults' value.",
        ),
    ],
) -> None:
    """Remove some settings of a profile, so that they return to the defaults."""
    config = get_state(ctx).config
    names = [_setting_key(key) for key in keys]
    refused = {**PROTECTED_SETTINGS, "url": "The URL of a profile cannot be unset."}
    _check_setting_keys(name, names, refused)
    profile = _changed_profile(config, name, {}, unset=names)
    config.add(profile, replace=True)
    config.save()
    emit(ctx, {**profile.summary(), "unset": sorted(names)})


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


@app.command(rich_help_panel=panels.BROWSE)
def groups(ctx: typer.Context) -> None:
    """List the groups of profiles."""
    config = get_state(ctx).config
    emit(
        ctx,
        [
            {"name": name, "profiles": members}
            for name, members in sorted(config.groups.items())
        ],
    )


@app.command("group-set", rich_help_panel=panels.WRITE)
def group_set(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Group name.")],
    profiles: Annotated[list[str], typer.Argument(help="Profiles in the group.")],
) -> None:
    """Create a group of profiles, or replace its profiles.

    The MCP server serves a group with 'plone-client mcp --group NAME'.
    """
    config = get_state(ctx).config
    members = config.set_group(name, profiles)
    config.save()
    emit(ctx, {"name": name, "profiles": members})


@app.command("group-remove", rich_help_panel=panels.WRITE)
def group_remove(
    ctx: typer.Context,
    name: Annotated[str, typer.Argument(help="Group name.")],
) -> None:
    """Remove a group; its profiles are kept."""
    config = get_state(ctx).config
    members = config.remove_group(name)
    config.save()
    emit(ctx, {"removed": name, "profiles": members})


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
    emit_connection(ctx, {"profile": profile.name, **result}, profile.name)
