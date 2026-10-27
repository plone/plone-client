"""The ``plone-client`` command line.

Needs the ``cli`` extra: ``pip install 'plone-client[cli]'``.
"""

from . import content
from . import panels
from . import profile
from . import site
from . import skill
from .app import app
from typer.core import MarkupMode
from typing import TextIO

import sys


for module in (content, site):
    app.registered_commands.extend(module.commands.registered_commands)
app.add_typer(site.users_app, name="users", rich_help_panel=panels.SITE)
app.add_typer(site.groups_app, name="groups", rich_help_panel=panels.SITE)
app.add_typer(site.registry_app, name="registry", rich_help_panel=panels.SITE)
app.add_typer(site.aliases_app, name="aliases", rich_help_panel=panels.SITE)
app.add_typer(profile.app, name="profile", rich_help_panel=panels.CONFIGURATION)
app.add_typer(skill.app, name="skill", rich_help_panel=panels.CONFIGURATION)


def help_markup(stream: TextIO | None = None) -> MarkupMode:
    """How ``--help`` is rendered for an output stream.

    :param stream: Where the help goes; standard output by default.
    :returns: ``"rich"`` (panels drawn as boxes) for a terminal, ``None``
        (plain text, same grouping) for a pipe or a file, which is how
        scripts and coding agents read it.
    """
    stream = sys.stdout if stream is None else stream
    return "rich" if stream.isatty() else None


def main() -> None:
    """Run the command line."""
    app.rich_markup_mode = help_markup()
    app()


__all__ = ["app", "main"]
