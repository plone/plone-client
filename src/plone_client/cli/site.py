"""Site commands: information, types, vocabularies, registry, users and groups."""

from . import panels
from .output import confirm
from .output import emit
from .output import parse_value
from .output import payload
from .output import PloneGroup
from .output import read_data
from .profile import _read_secret
from .profile import check_connection
from .profile import emit_connection
from .state import get_state
from itertools import islice
from typing import Annotated
from typing import Any

import typer


registry_app = typer.Typer(
    cls=PloneGroup,
    help="Browse and change the site's registry records.",
    no_args_is_help=True,
)
users_app = typer.Typer(
    cls=PloneGroup,
    help="Browse, create, change, and remove users.",
    no_args_is_help=True,
)
groups_app = typer.Typer(
    cls=PloneGroup,
    help="Browse, create, and remove groups, and manage their members.",
    no_args_is_help=True,
)
aliases_app = typer.Typer(
    cls=PloneGroup,
    help="Browse, add, and remove URL aliases (redirects) of items.",
    no_args_is_help=True,
)


commands = typer.Typer()
"""Site commands, merged into the root application."""


@commands.command(rich_help_panel=panels.CONFIGURATION)
def info(ctx: typer.Context) -> None:
    """Show which site and user the client connects with."""
    state = get_state(ctx)
    client = state.client
    profile = state.selected_profile()
    result = check_connection(client, client.username)
    emit_connection(
        ctx,
        {"profile": profile.name if profile else None, **result},
        profile.name if profile else "PROFILE",
    )


@commands.command(rich_help_panel=panels.SITE)
def types(
    ctx: typer.Context,
    portal_type: Annotated[
        str | None, typer.Argument(help="Type whose schema to show.")
    ] = None,
    addable_in: Annotated[
        str | None,
        typer.Option(help="List only the types that can be added in this folder."),
    ] = None,
) -> None:
    """List content types, or show the JSON schema of one."""
    client = get_state(ctx).client
    if portal_type:
        emit(ctx, client.types.get(portal_type))
    elif addable_in:
        emit(ctx, client.types.addable(addable_in))
    else:
        emit(
            ctx,
            [
                {
                    "id": entry["@id"].rsplit("/", 1)[-1],
                    "title": entry.get("title"),
                    "addable": entry.get("addable"),
                }
                for entry in client.types.list()
            ],
        )


@commands.command("block-types", rich_help_panel=panels.SITE)
def block_types(
    ctx: typer.Context,
    block_id: Annotated[
        str | None,
        typer.Argument(help="Block whose docs, schema and variations to show."),
    ] = None,
    for_item: Annotated[
        str | None,
        typer.Option(
            "--for", help="Only the blocks that editors can add to this item."
        ),
    ] = None,
    markdown: Annotated[
        bool, typer.Option("--markdown", help="Print Markdown instead of JSON.")
    ] = False,
) -> None:
    """List the blocks of the site, or show one (Volto's @blocks-schema).

    Without that service (older Volto, or a backend URL without
    frontend_url), Volto's core blocks are described instead, with
    "source": "builtin".
    """
    manager = get_state(ctx).client.block_types
    if markdown:
        typer.echo(manager.markdown(block_id, for_item))
    elif block_id:
        emit(ctx, manager.get(block_id, for_item))
    else:
        emit(ctx, manager.list(for_item))


@commands.command(rich_help_panel=panels.SITE)
def vocabulary(
    ctx: typer.Context,
    name: Annotated[
        str | None,
        typer.Argument(help="Vocabulary name; without it, list the vocabularies."),
    ] = None,
    title: Annotated[str | None, typer.Option(help="Filter terms by title.")] = None,
    limit: Annotated[int, typer.Option(help="Maximum number of terms.")] = 100,
) -> None:
    """List vocabularies, or the terms of one."""
    client = get_state(ctx).client
    if not name:
        emit(
            ctx,
            [entry["@id"].rsplit("/", 1)[-1] for entry in client.vocabularies.list()],
        )
        return
    terms = client.vocabularies.iter(name, title=title)
    emit(ctx, list(islice(terms, limit)))


@commands.command(rich_help_panel=panels.CONTENT_READ)
def sharing(
    ctx: typer.Context,
    ref: Annotated[str, typer.Argument(help="Path of the item.")] = "/",
    search: Annotated[
        str | None, typer.Option(help="Also list users and groups matching this.")
    ] = None,
) -> None:
    """Show the local roles of an item."""
    emit(ctx, get_state(ctx).client.sharing.get(ref, search=search))


@commands.command(rich_help_panel=panels.ADVANCED)
def request(
    ctx: typer.Context,
    method: Annotated[str, typer.Argument(help="GET, POST, PATCH, PUT or DELETE.")],
    ref: Annotated[
        str, typer.Argument(help="Path with the service, such as /news/@workflow.")
    ],
    param: Annotated[
        list[str] | None,
        typer.Option("--param", "-P", help="Query parameter key=value. Repeatable."),
    ] = None,
    data: Annotated[
        str | None,
        typer.Option("--data", "-d", help="JSON body; @file.json or - for stdin."),
    ] = None,
    header: Annotated[
        list[str] | None,
        typer.Option("--header", "-H", help="Header 'Name: value'. Repeatable."),
    ] = None,
) -> None:
    """Send any request to the site, for services without a command."""
    client = get_state(ctx).client
    params: list[tuple[str, Any]] = []
    for item in param or []:
        key, sep, value = item.partition("=")
        if not sep:
            raise ValueError(f"Expected key=value, got {item!r}")
        params.append((key, value))
    headers = {}
    for item in header or []:
        name, sep, value = item.partition(":")
        if not sep:
            raise ValueError(f"Expected 'Name: value', got {item!r}")
        headers[name.strip()] = value.strip()
    body = read_data(data) if data else None
    response = client.request(method, ref, params=params, json=body, headers=headers)
    if response.status_code == 204 or not response.content:
        emit(ctx, {"status": response.status_code})
    elif "json" in response.headers.get("Content-Type", ""):
        emit(ctx, response.json())
    else:
        typer.echo(response.text)


# ----------------------------------------------------------------------
# registry
# ----------------------------------------------------------------------


@registry_app.command("list", rich_help_panel=panels.BROWSE)
def registry_list(
    ctx: typer.Context,
    query: Annotated[
        str | None, typer.Argument(help="Text the record name must contain.")
    ] = None,
    limit: Annotated[int, typer.Option(help="Maximum number of records.")] = 100,
) -> None:
    """List records with their values."""
    records = islice(get_state(ctx).client.registry.list(query), limit)
    emit(ctx, [{"name": r["name"], "value": r.get("value")} for r in records])


@registry_app.command("get", rich_help_panel=panels.BROWSE)
def registry_get(
    ctx: typer.Context, key: Annotated[str, typer.Argument(help="Record name.")]
) -> None:
    """Print the value of a record."""
    emit(ctx, get_state(ctx).client.registry.get(key))


@registry_app.command("set", rich_help_panel=panels.WRITE)
def registry_set(
    ctx: typer.Context,
    key: Annotated[str, typer.Argument(help="Record name.")],
    value: Annotated[
        str, typer.Argument(help='New value, as JSON ("text", 10, true, [..]).')
    ],
) -> None:
    """Change the value of a record."""
    client = get_state(ctx).client
    client.registry.set(key, parse_value(value))
    emit(
        ctx,
        {key: client.registry.get(key)} if not client.dry_run else client.dry_run_log,
    )


# ----------------------------------------------------------------------
# users
# ----------------------------------------------------------------------


@users_app.command("list", rich_help_panel=panels.BROWSE)
def users_list(
    ctx: typer.Context,
    search: Annotated[
        str | None, typer.Option("--search", "-q", help="Text in id, name or email.")
    ] = None,
    group: Annotated[
        list[str] | None, typer.Option(help="Only members of this group.")
    ] = None,
    limit: Annotated[int, typer.Option(help="Maximum number of users.")] = 100,
) -> None:
    """List users."""
    emit(
        ctx, get_state(ctx).client.users.list(search=search, groups=group, limit=limit)
    )


@users_app.command("get", rich_help_panel=panels.BROWSE)
def users_get(
    ctx: typer.Context, user_id: Annotated[str, typer.Argument(help="User id.")]
) -> None:
    """Show a user."""
    emit(ctx, get_state(ctx).client.users.get(user_id))


@users_app.command("create", rich_help_panel=panels.WRITE)
def users_create(
    ctx: typer.Context,
    username: Annotated[str, typer.Argument(help="Login name.")],
    email: Annotated[str | None, typer.Option(help="Email address.")] = None,
    fullname: Annotated[str | None, typer.Option(help="Full name.")] = None,
    role: Annotated[
        list[str] | None, typer.Option(help="Global role. Repeatable.")
    ] = None,
    group: Annotated[list[str] | None, typer.Option(help="Group. Repeatable.")] = None,
    send_reset: Annotated[
        bool, typer.Option(help="Email the user a link to set the password.")
    ] = True,
    password_stdin: Annotated[
        bool,
        typer.Option("--password-stdin", help="Read the password from standard input."),
    ] = False,
    data: Annotated[
        str | None, typer.Option("--data", "-d", help="More fields, JSON.")
    ] = None,
) -> None:
    """Create a user; by default the user gets an email to set the password.

    With --password-stdin the password is set directly and no email is sent,
    which suits sites without a mail server.
    """
    body = payload(data, [], email=email, fullname=fullname)
    if role:
        body["roles"] = role
    if group:
        body["groups"] = group
    if password_stdin:
        body["password"] = _read_secret(True, "Password")
    if send_reset and "password" not in body:
        body["sendPasswordReset"] = True
    emit(ctx, get_state(ctx).client.users.create(username, body))


@users_app.command("update", rich_help_panel=panels.WRITE)
def users_update(
    ctx: typer.Context,
    user_id: Annotated[str, typer.Argument(help="User id.")],
    assignments: Annotated[
        list[str] | None,
        typer.Option("--set", "-s", help="Field: key=text or key:=json. Repeatable."),
    ] = None,
    data: Annotated[
        str | None, typer.Option("--data", "-d", help="Fields, JSON.")
    ] = None,
) -> None:
    """Change a user; roles:='{"Editor": true}' grants a role."""
    body = payload(data, assignments or [])
    if not body:
        raise ValueError("Nothing to change: give --data or --set")
    client = get_state(ctx).client
    client.users.update(user_id, body)
    emit(ctx, client.dry_run_log[-1] if client.dry_run else client.users.get(user_id))


@users_app.command("delete", rich_help_panel=panels.WRITE)
def users_delete(
    ctx: typer.Context,
    user_id: Annotated[str, typer.Argument(help="User id.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Do not ask.")] = False,
) -> None:
    """Delete a user."""
    confirm(ctx, f"Delete user {user_id}", yes)
    client = get_state(ctx).client
    client.users.delete(user_id)
    emit(ctx, {"deleted": user_id, "dry_run": client.dry_run})


# ----------------------------------------------------------------------
# groups
# ----------------------------------------------------------------------


@groups_app.command("list", rich_help_panel=panels.BROWSE)
def groups_list(
    ctx: typer.Context,
    query: Annotated[
        str | None, typer.Option("--query", "-q", help="Text in the id.")
    ] = None,
) -> None:
    """List groups."""
    emit(ctx, get_state(ctx).client.groups.list(query=query))


@groups_app.command("get", rich_help_panel=panels.BROWSE)
def groups_get(
    ctx: typer.Context, group_id: Annotated[str, typer.Argument(help="Group id.")]
) -> None:
    """Show a group and its members."""
    emit(ctx, get_state(ctx).client.groups.get(group_id))


@groups_app.command("create", rich_help_panel=panels.WRITE)
def groups_create(
    ctx: typer.Context,
    group_id: Annotated[str, typer.Argument(help="Group id.")],
    title: Annotated[str | None, typer.Option(help="Title.")] = None,
    description: Annotated[str | None, typer.Option(help="Description.")] = None,
    role: Annotated[
        list[str] | None, typer.Option(help="Global role. Repeatable.")
    ] = None,
) -> None:
    """Create a group."""
    body = payload(None, [], title=title, description=description)
    if role:
        body["roles"] = role
    emit(ctx, get_state(ctx).client.groups.create(group_id, body))


@groups_app.command("add-member", rich_help_panel=panels.MEMBERSHIP)
def groups_add_member(
    ctx: typer.Context,
    group_id: Annotated[str, typer.Argument(help="Group id.")],
    user_ids: Annotated[list[str], typer.Argument(help="User ids.")],
) -> None:
    """Add users to a group."""
    client = get_state(ctx).client
    client.groups.add_members(group_id, user_ids)
    emit(
        ctx,
        client.dry_run_log[-1]
        if client.dry_run
        else client.groups.get(group_id)["members"],
    )


@groups_app.command("remove-member", rich_help_panel=panels.MEMBERSHIP)
def groups_remove_member(
    ctx: typer.Context,
    group_id: Annotated[str, typer.Argument(help="Group id.")],
    user_ids: Annotated[list[str], typer.Argument(help="User ids.")],
) -> None:
    """Remove users from a group."""
    client = get_state(ctx).client
    client.groups.remove_members(group_id, user_ids)
    emit(
        ctx,
        client.dry_run_log[-1]
        if client.dry_run
        else client.groups.get(group_id)["members"],
    )


@groups_app.command("delete", rich_help_panel=panels.WRITE)
def groups_delete(
    ctx: typer.Context,
    group_id: Annotated[str, typer.Argument(help="Group id.")],
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Do not ask.")] = False,
) -> None:
    """Delete a group."""
    confirm(ctx, f"Delete group {group_id}", yes)
    client = get_state(ctx).client
    client.groups.delete(group_id)
    emit(ctx, {"deleted": group_id, "dry_run": client.dry_run})


# ----------------------------------------------------------------------
# aliases
# ----------------------------------------------------------------------


@aliases_app.command("list", rich_help_panel=panels.BROWSE)
def aliases_list(
    ctx: typer.Context,
    ref: Annotated[
        str, typer.Argument(help="Item; the site root lists every redirect.")
    ] = "/",
    query: Annotated[str | None, typer.Option(help="Filter, on the site root.")] = None,
) -> None:
    """List the aliases of an item, or every redirect of the site."""
    params = {"query": query} if query else {}
    emit(ctx, get_state(ctx).client.aliases.list(ref, **params))


@aliases_app.command("add", rich_help_panel=panels.WRITE)
def aliases_add(
    ctx: typer.Context,
    ref: Annotated[str, typer.Argument(help="Item the aliases point to.")],
    aliases: Annotated[list[str], typer.Argument(help="Old paths.")],
) -> None:
    """Make old paths redirect to an item."""
    client = get_state(ctx).client
    client.aliases.create(ref, aliases)
    emit(ctx, client.dry_run_log[-1] if client.dry_run else client.aliases.list(ref))


@aliases_app.command("remove", rich_help_panel=panels.WRITE)
def aliases_remove(
    ctx: typer.Context,
    ref: Annotated[str, typer.Argument(help="Item the aliases point to.")],
    aliases: Annotated[list[str], typer.Argument(help="Alias paths.")],
) -> None:
    """Remove aliases."""
    client = get_state(ctx).client
    client.aliases.delete(ref, aliases)
    emit(ctx, client.dry_run_log[-1] if client.dry_run else client.aliases.list(ref))
