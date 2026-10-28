"""``plone-client mcp``: serve sites to MCP clients over standard I/O."""

from ..exceptions import PloneConfigurationError
from ..profiles import Profile
from . import panels
from . import state as state_module
from .state import get_state
from .state import State
from typing import Annotated
from typing import Any

import typer


commands = typer.Typer()
"""The ``mcp`` command, merged into the root application."""


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
) -> None:
    """Serve sites as an MCP server, over standard input and output.

    Without --site, --group or --all, it serves the selected profile, as
    other commands use it. With several sites, every tool takes a 'site'
    argument. Secrets stay in the keyring. A read-only profile, or
    --read-only, refuses changes; with --dry-run the tools report the
    requests instead of sending them. Needs the 'mcp' extra.
    """
    try:
        from ..mcp_server import serve
        from ..mcp_server import Sites
    except ImportError:
        raise PloneConfigurationError(
            "The MCP server needs the 'mcp' extra: pip install 'plone-client[mcp]'"
        ) from None
    state = get_state(ctx)
    if not (site or group or every):
        profile = state.selected_profile()
        serve(Sites.from_client(state.client, name=profile.name if profile else "site"))
        return
    profiles = _profiles(state, site or [], group or [], every)
    serve(
        Sites.from_profiles(
            profiles,
            read_only=state.read_only,
            dry_run=state.dry_run,
            factory=_client,
        )
    )
