"""Commands for the high-level operations, which group several requests."""

from .. import blocks
from .. import operations
from ..operations import LeadImage
from . import panels
from .content import DataOption
from .content import SetOption
from .output import emit
from .output import parse_value
from .output import payload
from .state import get_state
from pathlib import Path
from typing import Annotated
from typing import Any

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


def _lead_image(lead: int | None, no_lead: bool) -> LeadImage:
    """The lead image asked for on the command line.

    :param lead: Position of the lead image among the files, counting from 1.
    :param no_lead: Whether there is no lead image.
    :returns: Index of the lead image among the files, ``"first"`` or ``None``.
    """
    if no_lead:
        return None
    if lead is not None:
        return lead - 1
    return "first"


LeadOption = Annotated[
    int | None,
    typer.Option(
        help="Position of the lead image among the files, 1 for the first; "
        "the first image by default.",
        min=1,
    ),
]
NoLeadOption = Annotated[
    bool, typer.Option("--no-lead", help="Do not set a lead image.")
]
BlocksOption = Annotated[
    str | None,
    typer.Option(
        "--blocks",
        help="Block types to produce, as JSON, such as "
        '\'{"codeBlock": {"style": "light"}, "slateTable": false}\'; '
        "merged over the profile's.",
    ),
]


def parse_blocks(raw: str | None) -> dict[str, Any] | None:
    """The ``--blocks`` option, parsed.

    :param raw: The JSON text, or ``None``.
    :returns: The setting, or ``None`` when not given.
    :raises ValueError: If it is not JSON, or not a valid setting.
    """
    if raw is None:
        return None
    return blocks.check_setting(parse_value(raw))


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
    files: Annotated[
        list[Path] | None,
        typer.Option("--file", help="File or image to upload inside the page."),
    ] = None,
    lead: LeadOption = None,
    no_lead: NoLeadOption = False,
    publish: PublishOption = None,
    blocks_setting: BlocksOption = None,
) -> None:
    """Create a page from Markdown or HTML, converted to blocks.

    Files given with --file are uploaded inside the page; the first image is
    its lead image unless --lead or --no-lead says otherwise. --blocks, and
    the profile's blocks setting, choose the block types. Needs the
    'markdown' extra, on Python 3.12 or later.
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
        files=files or (),
        lead_image=_lead_image(lead, no_lead),
        publish=publish,
        blocks_setting=parse_blocks(blocks_setting),
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
    lead: LeadOption = None,
    no_lead: NoLeadOption = False,
    publish: PublishOption = None,
) -> None:
    """Create an item with files and images inside it, and set its lead image.

    The lead image goes in the type's image field, or, on Volto sites, in
    an Image inside the item that preview_image_link points to.
    """
    client = get_state(ctx).client
    result = operations.create_with_files(
        client,
        parent,
        portal_type,
        files,
        data=payload(
            data, assignments or [], title=title, description=description, id=item_id
        ),
        lead_image=_lead_image(lead, no_lead),
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
    blocks_setting: BlocksOption = None,
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
        blocks_setting=parse_blocks(blocks_setting),
    )
    emit(ctx, result.to_dict())
