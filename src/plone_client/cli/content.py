"""Content commands: read, search, create, change and remove items."""

from .. import blocks as blocks_helpers
from ..utils import uid_from_ref
from .output import confirm
from .output import emit
from .output import parse_assignments
from .output import payload
from .output import summary
from .state import get_state
from pathlib import Path
from typing import Annotated
from typing import Any

import sys
import typer


Ref = Annotated[
    str,
    typer.Argument(
        help="Path (/news/item), site URL, uid:<UID> or resolveuid link.",
        show_default=False,
    ),
]
DataOption = Annotated[
    str | None,
    typer.Option(
        "--data",
        "-d",
        help="JSON object with field values; @file.json reads a file, - reads stdin.",
    ),
]
SetOption = Annotated[
    list[str] | None,
    typer.Option(
        "--set",
        "-s",
        help="Field value: key=text, or key:=json (subjects:='[\"a\"]'). Repeatable.",
    ),
]
FullOption = Annotated[
    bool, typer.Option("--full", help="Print the whole item, not a summary.")
]


commands = typer.Typer()
"""Content commands, merged into the root application."""


@commands.command(rich_help_panel="Content")
def get(
    ctx: typer.Context,
    ref: Ref = "/",
    expand: Annotated[
        list[str] | None,
        typer.Option(help="Component to expand: breadcrumbs, translations…"),
    ] = None,
    fullobjects: Annotated[
        bool, typer.Option(help="Serialize contained items in full.")
    ] = False,
    items: Annotated[bool, typer.Option(help="Include the contained items.")] = True,
    version: Annotated[
        str | None, typer.Option(help="Version from the history.")
    ] = None,
) -> None:
    """Print an item."""
    client = get_state(ctx).client
    emit(
        ctx,
        client.content.get(
            ref,
            expand=expand,
            fullobjects=fullobjects,
            include_items=None if items else False,
            version=version,
        ),
    )


@commands.command("ls", rich_help_panel="Content")
def list_children(
    ctx: typer.Context,
    ref: Ref = "/",
    portal_type: Annotated[
        list[str] | None, typer.Option("--type", "-t", help="Only this type.")
    ] = None,
    metadata: Annotated[
        list[str] | None,
        typer.Option("--metadata", "-m", help="Extra catalog column; _all for all."),
    ] = None,
    limit: Annotated[int, typer.Option(help="Maximum number of items.")] = 100,
) -> None:
    """List the items inside a folder, in order."""
    client = get_state(ctx).client
    emit(
        ctx,
        list(
            client.content.children(
                ref, portal_type=portal_type, metadata_fields=metadata, limit=limit
            )
        ),
    )


@commands.command(rich_help_panel="Content")
def search(
    ctx: typer.Context,
    ref: Ref = "/",
    text: Annotated[
        str | None, typer.Option("--text", "-q", help="Full-text search.")
    ] = None,
    portal_type: Annotated[
        list[str] | None, typer.Option("--type", "-t", help="Content type.")
    ] = None,
    state: Annotated[
        list[str] | None, typer.Option("--state", help="Workflow state.")
    ] = None,
    depth: Annotated[
        int | None,
        typer.Option(help="Levels below the folder: 0 is itself, 1 its children."),
    ] = None,
    index: Annotated[
        list[str] | None,
        typer.Option(
            "--index",
            "-i",
            help="Other index: Subject=plone, or key:=json for options. Repeatable.",
        ),
    ] = None,
    sort_on: Annotated[str | None, typer.Option(help="Index to sort on.")] = None,
    reverse: Annotated[bool, typer.Option(help="Sort descending.")] = False,
    metadata: Annotated[
        list[str] | None,
        typer.Option("--metadata", "-m", help="Extra catalog column; _all for all."),
    ] = None,
    fullobjects: Annotated[
        bool, typer.Option(help="Return full serializations (slow).")
    ] = False,
    limit: Annotated[int, typer.Option(help="Maximum number of results.")] = 50,
    count: Annotated[
        bool, typer.Option("--count", help="Print only the number of results.")
    ] = False,
) -> None:
    """Search the catalog, inside a folder (the whole site by default)."""
    client = get_state(ctx).client
    path = client.content.resolve(ref)
    indexes: dict[str, Any] = parse_assignments(index or [])
    if count:
        total = client.search.count(
            path,
            query=indexes,
            portal_type=portal_type,
            review_state=state,
            text=text,
            depth=depth,
        )
        emit(ctx, {"items_total": total})
        return
    results = client.search.iter(
        path,
        query=indexes,
        portal_type=portal_type,
        review_state=state,
        text=text,
        depth=depth,
        sort_on=sort_on,
        sort_order="descending" if reverse else None,
        metadata_fields=metadata,
        fullobjects=fullobjects,
        limit=limit,
        b_size=min(limit, 100),
    )
    emit(ctx, list(results))


@commands.command(rich_help_panel="Content")
def create(
    ctx: typer.Context,
    parent: Annotated[str, typer.Argument(help="Path of the folder.")],
    portal_type: Annotated[str, typer.Argument(help="Content type, such as Document.")],
    title: Annotated[str | None, typer.Option(help="Title.")] = None,
    item_id: Annotated[
        str | None, typer.Option("--id", help="Id (short name).")
    ] = None,
    description: Annotated[str | None, typer.Option(help="Description.")] = None,
    data: DataOption = None,
    assignments: SetOption = None,
    with_blocks: Annotated[
        bool,
        typer.Option(
            "--blocks/--no-blocks",
            help="Add title and description blocks when no blocks are given.",
        ),
    ] = True,
    publish: Annotated[
        str | None,
        typer.Option(help="Run this workflow transition after creating, e.g. publish."),
    ] = None,
    full: FullOption = False,
) -> None:
    """Create an item inside a folder.

    Read the @id of the result: Plone may change the id that was asked for.
    """
    client = get_state(ctx).client
    body = payload(
        data, assignments or [], title=title, id=item_id, description=description
    )
    if with_blocks and "blocks" not in body:
        body.update(
            blocks_helpers.build(blocks_helpers.title(), blocks_helpers.description())
        )
    item = client.content.create(parent, portal_type, body)
    if publish and not client.dry_run:
        client.workflow.transition(item["@id"], publish)
        item = client.content.get(item["@id"])
    emit(ctx, item if full or client.dry_run else summary(item))


@commands.command(rich_help_panel="Content")
def update(
    ctx: typer.Context,
    ref: Ref,
    title: Annotated[str | None, typer.Option(help="Title.")] = None,
    description: Annotated[str | None, typer.Option(help="Description.")] = None,
    data: DataOption = None,
    assignments: SetOption = None,
    lock_token: Annotated[
        str | None, typer.Option(help="Token of a lock held on the item.")
    ] = None,
    full: FullOption = False,
) -> None:
    """Change fields of an item."""
    client = get_state(ctx).client
    body = payload(data, assignments or [], title=title, description=description)
    if not body:
        raise ValueError("Nothing to change: give --data, --set, --title…")
    item = client.content.update(ref, body, lock_token=lock_token)
    emit(ctx, item if full or client.dry_run or item is None else summary(item))


@commands.command(rich_help_panel="Content")
def delete(
    ctx: typer.Context,
    refs: Annotated[list[str], typer.Argument(help="Items to delete.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Do not ask.")] = False,
) -> None:
    """Delete items."""
    confirm(ctx, f"Delete {len(refs)} item(s)", yes)
    client = get_state(ctx).client
    deleted = []
    for ref in refs:
        path = client.content.resolve(ref)
        client.content.delete(path)
        deleted.append(path)
    emit(ctx, {"deleted": deleted, "dry_run": client.dry_run})


@commands.command(rich_help_panel="Content")
def copy(
    ctx: typer.Context,
    sources: Annotated[list[str], typer.Argument(help="Items to copy.")],
    target: Annotated[str, typer.Option("--to", help="Folder to copy into.")],
) -> None:
    """Copy items into a folder."""
    client = get_state(ctx).client
    emit(
        ctx,
        client.content.copy([client.content.resolve(s) for s in sources], target),
    )


@commands.command(rich_help_panel="Content")
def move(
    ctx: typer.Context,
    sources: Annotated[list[str], typer.Argument(help="Items to move.")],
    target: Annotated[str, typer.Option("--to", help="Folder to move into.")],
) -> None:
    """Move items into a folder."""
    client = get_state(ctx).client
    emit(
        ctx,
        client.content.move([client.content.resolve(s) for s in sources], target),
    )


@commands.command(
    rich_help_panel="Content",
    # so that a negative delta (-1) is read as an argument, not an option
    context_settings={"ignore_unknown_options": True},
)
def order(
    ctx: typer.Context,
    folder: Annotated[str, typer.Argument(help="Path of the folder.")],
    item_id: Annotated[str, typer.Argument(help="Id of the item to move.")],
    delta: Annotated[
        str,
        typer.Argument(
            help="top, bottom, up, down, or a number of positions (-2 is two up)."
        ),
    ],
) -> None:
    """Move an item within its folder."""
    client = get_state(ctx).client
    steps = {"up": -1, "down": 1}
    if delta in ("top", "bottom"):
        position: Any = delta
    elif delta in steps:
        position = steps[delta]
    else:
        try:
            position = int(delta)
        except ValueError:
            raise ValueError(f"Not a valid delta: {delta!r}") from None
    client.content.order(folder, item_id, position)
    emit(ctx, [entry["@id"] for entry in client.content.children(folder)])


@commands.command(rich_help_panel="Content")
def workflow(
    ctx: typer.Context,
    ref: Ref,
    transition: Annotated[
        str | None,
        typer.Argument(help="Transition to run; without it, list the available ones."),
    ] = None,
    comment: Annotated[
        str | None, typer.Option(help="Comment for the history.")
    ] = None,
    effective: Annotated[
        str | None, typer.Option(help="Publication date, ISO 8601.")
    ] = None,
    expires: Annotated[
        str | None, typer.Option(help="Expiration date, ISO 8601.")
    ] = None,
    recursive: Annotated[
        bool, typer.Option(help="Also run it on the items inside a folder.")
    ] = False,
) -> None:
    """Show the workflow state of an item, or run a transition."""
    client = get_state(ctx).client
    if transition is None:
        info = client.workflow.info(ref)
        emit(
            ctx,
            {
                "state": info.get("state"),
                "transitions": [
                    entry["@id"].rsplit("/", 1)[-1]
                    for entry in info.get("transitions", [])
                ],
                "history": info.get("history", []),
            },
        )
        return
    emit(
        ctx,
        client.workflow.transition(
            ref,
            transition,
            comment=comment,
            effective=effective,
            expires=expires,
            include_children=recursive,
        ),
    )


@commands.command(rich_help_panel="Content")
def history(ctx: typer.Context, ref: Ref) -> None:
    """List the versions and workflow history of an item."""
    emit(ctx, get_state(ctx).client.history.list(ref))


@commands.command(rich_help_panel="Content")
def blocks(
    ctx: typer.Context,
    ref: Ref,
    links: Annotated[
        bool, typer.Option("--links", help="List the links found in each block.")
    ] = False,
) -> None:
    """Summarize the blocks of an item, nested ones included."""
    client = get_state(ctx).client
    item = client.content.get(ref, include_items=False)
    rows = []
    for block_id, block in blocks_helpers.iter_blocks(
        item.get("blocks"), item.get("blocks_layout")
    ):
        row: dict[str, Any] = {"id": block_id, "@type": block.get("@type")}
        text = block.get("plaintext")
        if text:
            row["text"] = text[:120]
        if links:
            found = list(blocks_helpers.iter_links(block))
            if found:
                row["links"] = found
        rows.append(row)
    emit(ctx, rows)


@commands.command(rich_help_panel="Content")
def resolve(ctx: typer.Context, ref: Ref) -> None:
    """Print the path, URL and UID of an item."""
    client = get_state(ctx).client
    uid = uid_from_ref(ref)
    entry = client.content.find_by_uid(uid) if uid else None
    path = client.path(entry["@id"]) if entry else client.content.resolve(ref)
    if entry is None:
        entry = client.content.get(path, include_items=False)
    emit(
        ctx,
        {
            "path": path,
            "url": client.site_url(path),
            "UID": entry.get("UID") or uid,
            "@type": entry.get("@type"),
            "title": entry.get("title"),
        },
    )


@commands.command(rich_help_panel="Files")
def upload(
    ctx: typer.Context,
    parent: Annotated[str, typer.Argument(help="Path of the folder.")],
    files: Annotated[
        list[Path],
        typer.Argument(help="Files to upload.", exists=True, dir_okay=False),
    ],
    portal_type: Annotated[
        str | None,
        typer.Option("--type", "-t", help="Content type; Image or File by default."),
    ] = None,
    title: Annotated[str | None, typer.Option(help="Title (one file only).")] = None,
    item_id: Annotated[
        str | None, typer.Option("--id", help="Id (one file only).")
    ] = None,
    tus: Annotated[
        bool, typer.Option("--tus", help="Send in chunks, for large files.")
    ] = False,
) -> None:
    """Upload files as File or Image items."""
    if (title or item_id) and len(files) > 1:
        raise ValueError("--title and --id need a single file")
    client = get_state(ctx).client
    results = []
    for path in files:
        if tus:
            url = client.files.tus_upload(parent, path, portal_type=portal_type)
            results.append({"@id": url})
            continue
        extra = {k: v for k, v in (("title", title), ("id", item_id)) if v}
        item = client.files.upload(parent, path, portal_type=portal_type, **extra)
        results.append(item if client.dry_run else summary(item))
    emit(ctx, results)


@commands.command(rich_help_panel="Files")
def download(
    ctx: typer.Context,
    ref: Ref,
    output: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="File to write; - for stdout."),
    ] = None,
    field: Annotated[str, typer.Option(help="Field holding the file.")] = "",
) -> None:
    """Download the file or image of an item."""
    client = get_state(ctx).client
    path = client.content.resolve(ref)
    item = client.content.get(path, include_items=False)
    field = field or ("image" if item.get("@type") == "Image" else "file")
    data = client.files.download(path, field=field)
    if output is not None and str(output) == "-":
        sys.stdout.buffer.write(data)
        return
    value = item.get(field) or {}
    target = output or Path(value.get("filename") or path.rsplit("/", 1)[-1])
    target.write_bytes(data)
    emit(
        ctx,
        {
            "path": str(target),
            "size": len(data),
            "content-type": value.get("content-type"),
        },
    )
