"""The ``plone-client`` command line.

Needs the ``cli`` extra: ``pip install 'plone-client[cli]'``.
"""

from . import content
from . import panels
from . import profile
from . import site
from . import skill
from .app import app


for module in (content, site):
    app.registered_commands.extend(module.commands.registered_commands)
app.add_typer(site.users_app, name="users", rich_help_panel=panels.SITE)
app.add_typer(site.groups_app, name="groups", rich_help_panel=panels.SITE)
app.add_typer(site.registry_app, name="registry", rich_help_panel=panels.SITE)
app.add_typer(site.aliases_app, name="aliases", rich_help_panel=panels.SITE)
app.add_typer(profile.app, name="profile", rich_help_panel=panels.CONFIGURATION)
app.add_typer(skill.app, name="skill", rich_help_panel=panels.CONFIGURATION)


def main() -> None:
    """Run the command line."""
    app()


__all__ = ["app", "main"]
