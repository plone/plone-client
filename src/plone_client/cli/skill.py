"""``plone-client skill``: the agent skill shipped with plone-client."""

from . import panels
from .output import emit
from .output import PloneGroup
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Annotated

import typer


app = typer.Typer(
    cls=PloneGroup,
    help="Show or install the agent skill that teaches coding agents this tool.",
    no_args_is_help=True,
)

SKILL_NAME = "plone-client"
SKILL_FILE = "SKILL.md"
PROJECT_DIR = Path(".claude") / "skills"
USER_DIR = Path("~") / ".claude" / "skills"


def skill_files(
    folder: Traversable | None = None, prefix: str = ""
) -> dict[str, Traversable]:
    """Files of the skill.

    :param folder: Folder to list; the root of the skill by default.
    :param prefix: Path of that folder inside the skill.
    :returns: Each file, by its path inside the skill.
    """
    folder = folder or files("plone_client").joinpath("skill")
    found: dict[str, Traversable] = {}
    for entry in folder.iterdir():
        path = f"{prefix}{entry.name}"
        if entry.is_dir():
            found.update(skill_files(entry, f"{path}/"))
        elif entry.name.endswith(".md"):
            found[path] = entry
    return found


def skill_text(name: str = SKILL_FILE) -> str:
    """Contents of a file of the skill.

    :param name: Path of the file inside the skill.
    :returns: The Markdown text.
    """
    return skill_files()[name].read_text(encoding="utf-8")


@app.command(rich_help_panel=panels.BROWSE)
def show(
    name: Annotated[
        str, typer.Argument(help="File of the skill, such as references/blocks.md.")
    ] = SKILL_FILE,
) -> None:
    """Print the skill's SKILL.md, or another file of the skill."""
    if name not in skill_files():
        known = ", ".join(sorted(skill_files()))
        raise typer.BadParameter(f"{name} is not in the skill: {known}")
    typer.echo(skill_text(name), nl=False)


@app.command(rich_help_panel=panels.WRITE)
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

    The skill goes in <directory>/plone-client/, with SKILL.md and its
    references, where agents that read Agent Skills, such as Claude Code,
    find it.
    """
    base = directory or (USER_DIR if user else PROJECT_DIR)
    root = base.expanduser() / SKILL_NAME
    replaced = (root / SKILL_FILE).exists()
    for name in skill_files():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(skill_text(name), encoding="utf-8")
    emit(ctx, {"installed": str(root / SKILL_FILE), "replaced": replaced})
