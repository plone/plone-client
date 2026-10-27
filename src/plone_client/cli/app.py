"""The ``plone-client`` Typer application and its global options."""

from .output import RootGroup
from .state import State
from pathlib import Path
from typing import Annotated

import logging
import typer


app = typer.Typer(
    cls=RootGroup,
    name="plone-client",
    help=(
        "plone-client — manage the content and settings of Plone sites "
        "through plone.restapi.\n\n"
        "Pick a site with a profile (plone-client profile add), then read and "
        "change its content with the commands below.\n\n"
        "Results are printed as JSON on standard output; errors as JSON on "
        "standard error, with exit codes 3 (configuration), 4 (not allowed), "
        "5 (not found), 6 (invalid request), 7 (read-only), 8 (connection) "
        "and 9 (server error). Run plone-client COMMAND --help for the "
        "options of each command."
    ),
    no_args_is_help=True,
    pretty_exceptions_enable=False,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)


def _version(value: bool) -> None:
    """Print the version and exit.

    :param value: Whether ``--version`` was given.
    """
    if value:
        from .. import __version__

        typer.echo(__version__)
        raise typer.Exit()


@app.callback()
def main(
    ctx: typer.Context,
    profile: Annotated[
        str,
        typer.Option(
            "--profile", "-p", help="Profile to use.", envvar="PLONE_CLIENT_PROFILE"
        ),
    ] = "",
    url: Annotated[
        str,
        typer.Option(
            "--url",
            help="Site URL, instead of a profile; the password comes from "
            "$PLONE_CLIENT_PASSWORD.",
        ),
    ] = "",
    username: Annotated[
        str, typer.Option("--username", "-u", help="Login name, with --url.")
    ] = "",
    config: Annotated[
        Path | None,
        typer.Option(
            "--config",
            help="Configuration file.",
            envvar="PLONE_CLIENT_CONFIG",
            dir_okay=False,
        ),
    ] = None,
    read_only: Annotated[
        bool, typer.Option("--read-only", help="Refuse any change to the site.")
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run", "-n", help="Print the changes instead of sending them."
        ),
    ] = False,
    fields: Annotated[
        str,
        typer.Option(
            "--fields",
            "-f",
            help="Comma separated keys to keep in the output, such as "
            "'@id,title,review_state'.",
        ),
    ] = "",
    compact: Annotated[
        bool, typer.Option("--compact", "-c", help="Print JSON on one line.")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Log each request to stderr.")
    ] = False,
    version: Annotated[
        bool,
        typer.Option(
            "--version", callback=_version, is_eager=True, help="Show the version."
        ),
    ] = False,
) -> None:
    """Manage content and settings of Plone sites through plone.restapi."""
    if verbose:
        logging.basicConfig(format="%(levelname)s %(message)s")
        logging.getLogger("plone_client").setLevel(logging.DEBUG)
    ctx.obj = state = State(
        profile=profile,
        url=url,
        username=username,
        config_file=config,
        read_only=read_only,
        dry_run=dry_run,
        fields=[name.strip() for name in fields.split(",") if name.strip()],
        compact=compact,
    )
    ctx.call_on_close(state.close)
