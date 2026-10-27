"""Commands for the high-level operations, which group several requests."""

from .. import operations
from ..operations import LeadImage
from . import panels
from .content import DataOption
from .content import SetOption
from .output import emit
from .output import payload
from .state import get_state
from pathlib import Path
from typing import Annotated

import sys
import typer


commands = typer.Typer()
"""Operation commands, merged into the root application."""

PublishOption = Annotated[
    str | None,
    typer.Option(help="Run this workflow transition at the end, e.g. publish."),
]


def _read_source(source: str) -> str:
    """Read the text of a page.

    :param source: Path of a file, or ``-`` for standard input.
    :returns: The text.
    """
    if source == "-":
        return sys.stdin.read()
    return Path(source).expanduser().read_text()


@commands.command("create-page", rich_help_panel=panels.CONTENT_CHANGE)
def create_page(
    ctx: typer.Context,
    parent: Annotated[str, typer.Argument(help="Path of the folder.")],
    source: Annotated[
        str, typer.Argument(help="Markdown or HTML file; - reads standard input.")
    ],
    html: Annotated[
        bool, typer.Option("--html", help="The source is HTML, not Markdown.")
    ] = False,
    title: Annotated[
        str | None,
        typer.Option(help="Title; the leading # heading by default."),
    ] = None,
    description: Annotated[str | None, typer.Option(help="Description.")] = None,
    portal_type: Annotated[
        str, typer.Option("--type", "-t", help="Content type, with blocks.")
    ] = "Document",
    item_id: Annotated[
        str | None, typer.Option("--id", help="Id (short name).")
    ] = None,
    data: DataOption = None,
    assignments: SetOption = None,
    publish: PublishOption = None,
) -> None:
    """Create a page from Markdown or HTML, converted to blocks.

    Needs the 'markdown' extra, on Python 3.12 or later.
    """
    client = get_state(ctx).client
    is_html = html or (
        source != "-" and Path(source).suffix.lower() in (".html", ".htm")
    )
    result = operations.create_page(
        client,
        parent,
        _read_source(source),
        source_format="html" if is_html else "markdown",
        portal_type=portal_type,
        title=title,
        description=description,
        data=payload(data, assignments or [], id=item_id),
        publish=publish,
    )
    emit(ctx, result.to_dict())


@commands.command("create-with-files", rich_help_panel=panels.CONTENT_CHANGE)
def create_with_files(
    ctx: typer.Context,
    parent: Annotated[str, typer.Argument(help="Path of the folder.")],
    portal_type: Annotated[
        str, typer.Argument(help="Content type, such as 'News Item'.")
    ],
    files: Annotated[
        list[Path],
        typer.Argument(help="Files and images to upload inside the item."),
    ],
    title: Annotated[str | None, typer.Option(help="Title.")] = None,
    description: Annotated[str | None, typer.Option(help="Description.")] = None,
    item_id: Annotated[
        str | None, typer.Option("--id", help="Id (short name).")
    ] = None,
    data: DataOption = None,
    assignments: SetOption = None,
    lead: Annotated[
        int | None,
        typer.Option(
            help="Position of the lead image among the files, 1 for the first; "
            "the first image by default.",
            min=1,
        ),
    ] = None,
    no_lead: Annotated[
        bool, typer.Option("--no-lead", help="Do not set a lead image.")
    ] = False,
    publish: PublishOption = None,
) -> None:
    """Create an item with files and images inside it, and set its lead image.

    The lead image goes in the type's image field, or, on Volto sites, in
    an Image inside the item that preview_image_link points to.
    """
    client = get_state(ctx).client
    lead_image: LeadImage = "first"
    if no_lead:
        lead_image = None
    elif lead is not None:
        lead_image = lead - 1
    result = operations.create_with_files(
        client,
        parent,
        portal_type,
        files,
        data=payload(
            data, assignments or [], title=title, description=description, id=item_id
        ),
        lead_image=lead_image,
        publish=publish,
    )
    emit(ctx, result.to_dict())


@commands.command("upload-tree", rich_help_panel=panels.CONTENT_FILES)
def upload_tree(
    ctx: typer.Context,
    source: Annotated[
        Path,
        typer.Argument(
            help="Local folder whose contents to upload.",
            exists=True,
            file_okay=False,
        ),
    ],
    parent: Annotated[str, typer.Argument(help="Folder of the site to upload into.")],
    folder_type: Annotated[
        str, typer.Option(help="Content type for folders.")
    ] = "Document",
    convert_pages: Annotated[
        bool,
        typer.Option(
            "--pages",
            help="Turn Markdown and HTML files into pages (needs the 'markdown' "
            "extra); index.md or README.md fills its folder's page.",
        ),
    ] = False,
    include_hidden: Annotated[
        bool, typer.Option("--hidden", help="Also upload names starting with a dot.")
    ] = False,
    publish: PublishOption = None,
) -> None:
    """Upload a local folder as pages, files and images, keeping its structure."""
    client = get_state(ctx).client
    result = operations.upload_tree(
        client,
        source,
        parent,
        folder_type=folder_type,
        convert_pages=convert_pages,
        include_hidden=include_hidden,
        publish=publish,
    )
    emit(ctx, result.to_dict())
