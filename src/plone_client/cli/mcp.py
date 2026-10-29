"""``plone-client mcp``: serve sites to MCP clients, and manage the token of
the HTTP server with ``plone-client mcp-token``."""

from .. import credentials
from ..exceptions import PloneConfigurationError
from ..profiles import Profile
from . import panels
from . import state as state_module
from .output import emit
from .output import PloneGroup
from .profile import _read_secret
from .state import get_state
from .state import State
from typing import Annotated
from typing import Any

import typer


commands = typer.Typer()
"""The ``mcp`` command, merged into the root application."""

token_app = typer.Typer(
    cls=PloneGroup,
    help="Manage the token MCP clients send to 'plone-client mcp --http'.",
    no_args_is_help=True,
)


def _profiles(
    state: State, sites: list[str], groups: list[str], every: bool
) -> list[Profile]:
    """Profiles named with ``--site``, ``--group`` and ``--all``.

    :param state: The command line state.
    :param sites: Profile names.
    :param groups: Group names.
    :param every: Serve every profile.
    :returns: The profiles, each once: every profile with ``--all``, then
        those of ``--site``, then those of the groups.
    :raises PloneConfigurationError: If one is unknown, or ``--profile`` or
        ``--url`` is given too.
    """
    if state.profile or state.url:
        raise PloneConfigurationError(
            "Use --profile or --url for one site, or --site, --group and --all "
            "for several; not both"
        )
    config = state.config
    chosen = (
        [config.profiles[name] for name in sorted(config.profiles)] if every else []
    )
    chosen += [config.get(name) for name in sites]
    for group in groups:
        chosen += config.group(group)
    if not chosen:
        raise PloneConfigurationError("There are no profiles to serve")
    unique: dict[str, Profile] = {}
    for profile in chosen:
        unique.setdefault(profile.name, profile)
    return list(unique.values())


def _client(**settings: Any) -> Any:
    """A client, built where the rest of the command line builds them.

    :param settings: Keyword arguments for the client.
    :returns: The client.
    """
    # Looked up at call time, so tests can replace it
    return state_module.PloneClient(**settings)  # type: ignore[attr-defined]


@commands.command(rich_help_panel=panels.ADVANCED)
def mcp(
    ctx: typer.Context,
    site: Annotated[
        list[str] | None,
        typer.Option(help="Profile to serve; repeat it for several sites."),
    ] = None,
    group: Annotated[
        list[str] | None,
        typer.Option(help="Group of profiles to serve (see 'profile groups')."),
    ] = None,
    every: Annotated[bool, typer.Option("--all", help="Serve every profile.")] = False,
    tool: Annotated[
        list[str] | None,
        typer.Option(help="Offer only this tool; repeat it for several."),
    ] = None,
    http: Annotated[
        bool,
        typer.Option("--http", help="Serve over streamable HTTP, with a bearer token."),
    ] = False,
    host: Annotated[
        str, typer.Option(help="Address to listen on, with --http.")
    ] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Port to listen on, with --http.")] = 8000,
) -> None:
    """Serve sites as an MCP server, over standard input and output or HTTP.

    Without --site, --group or --all, it serves the selected profile, as
    other commands use it. With several sites, every tool takes a 'site'
    argument. Secrets stay in the keyring. A read-only profile, or
    --read-only, refuses changes; with --dry-run the tools report the
    requests instead of sending them. --tool keeps the list of tools the
    model reads short. With --http, clients must send the token of
    'plone-client mcp-token generate'. Needs the 'mcp' extra.
    """
    try:
        from ..mcp_server import HTTPSettings
        from ..mcp_server import serve
        from ..mcp_server import Sites
    except ImportError:
        raise PloneConfigurationError(
            "The MCP server needs the 'mcp' extra: pip install 'plone-client[mcp]'"
        ) from None
    state = get_state(ctx)
    # Look up the token first, so a missing one stops before any connection
    settings = (
        HTTPSettings(credentials.get_mcp_token(), host=host, port=port)
        if http
        else None
    )
    if not (site or group or every):
        profile = state.selected_profile()
        serve(
            Sites.from_client(state.client, name=profile.name if profile else "site"),
            tool,
            settings,
        )
        return
    profiles = _profiles(state, site or [], group or [], every)
    serve(
        Sites.from_profiles(
            profiles,
            read_only=state.read_only,
            dry_run=state.dry_run,
            factory=_client,
        ),
        tool,
        settings,
    )


@token_app.command(rich_help_panel=panels.WRITE)
def generate(ctx: typer.Context) -> None:
    """Make a new random token, store it in the keyring, and print it.

    A token stored before is replaced: clients that use it are refused.
    """
    emit(ctx, {"token": credentials.generate_mcp_token(), "stored": "keyring"})


@token_app.command("set", rich_help_panel=panels.WRITE)
def set_token(
    ctx: typer.Context,
    token_stdin: Annotated[
        bool,
        typer.Option("--token-stdin", help="Read the token from standard input."),
    ] = False,
) -> None:
    """Store a token of your own in the keyring; it needs 32 characters."""
    credentials.set_mcp_token(_read_secret(token_stdin, "Token"))
    emit(ctx, {"token": "stored", "stored": "keyring"})


@token_app.command(rich_help_panel=panels.WRITE)
def delete(ctx: typer.Context) -> None:
    """Remove the token from the keyring."""
    emit(ctx, {"deleted": credentials.delete_mcp_token()})
