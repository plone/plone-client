"""``plone-client skill``: the agent skill shipped with plone-client."""

from .output import emit
from .output import PloneGroup
from importlib.resources import files
from pathlib import Path
from typing import Annotated

import typer


app = typer.Typer(
    cls=PloneGroup,
    help="Show or install the agent skill that teaches coding agents this tool.",
    no_args_is_help=True,
)

SKILL_NAME = "plone-client"
PROJECT_DIR = Path(".claude") / "skills"
USER_DIR = Path("~") / ".claude" / "skills"


def skill_text() -> str:
    """Contents of the skill's ``SKILL.md``.

    :returns: The Markdown text.
    """
    return files("plone_client").joinpath("skill", "SKILL.md").read_text()


@app.command()
def show() -> None:
    """Print the skill's SKILL.md."""
    typer.echo(skill_text(), nl=False)


@app.command()
def install(
    ctx: typer.Context,
    user: Annotated[
        bool,
        typer.Option("--user", help=f"Install in {USER_DIR}, for every project."),
    ] = False,
    directory: Annotated[
        Path | None,
        typer.Option(
            "--dir",
            help=f"Skills directory to install in; {PROJECT_DIR} by default.",
            show_default=False,
        ),
    ] = None,
) -> None:
    """Install the skill, replacing an older copy.

    The skill goes in <directory>/plone-client/SKILL.md, where agents that
    read Agent Skills, such as Claude Code, find it.
    """
    base = directory or (USER_DIR if user else PROJECT_DIR)
    target = base.expanduser() / SKILL_NAME / "SKILL.md"
    replaced = target.exists()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(skill_text())
    emit(ctx, {"installed": str(target), "replaced": replaced})
