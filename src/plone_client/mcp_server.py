"""An MCP server for Plone sites, built on the client and its operations.

The server gives chat assistants and agents without a shell the same access
the command line gives: the same profiles, secrets in the keyring, and the
same ``read_only`` and ``dry_run`` switches. It speaks over standard input
and output, or over streamable HTTP with a bearer token, for one site or
several::

    pip install 'plone-client[mcp]'
    plone-client mcp --profile blog
    plone-client mcp --site blog --site docs
    plone-client mcp --group customer
    plone-client mcp --all
    plone-client mcp --profile blog --http --port 8000

Rather than one tool per ``plone.restapi`` service, it offers the everyday
reads, the high-level operations of :mod:`plone_client.operations`, and one
tool for any other service. With several sites, every tool takes a ``site``
argument, and ``list_sites`` describes them. Tools that change a site are
only offered when at least one site accepts changes; a change to a read-only
site is refused before it is sent. Each site also has read-only resources,
such as ``plone://blog/blocks``, for users to attach to a conversation.
"""

from . import __version__
from . import blocks
from . import operations
from .client import PloneClient
from .exceptions import error_payload
from .exceptions import PloneClientError
from .exceptions import PloneConfigurationError
from .exceptions import PloneNotFoundError
from .profiles import Profile
from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Iterator
from dataclasses import dataclass
from dataclasses import field
from functools import wraps
from importlib.util import find_spec
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ResourceError
from mcp.server.mcpserver.exceptions import ResourceNotFoundError
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field
from starlette.responses import JSONResponse
from starlette.types import ASGIApp
from starlette.types import Receive
from starlette.types import Scope
from starlette.types import Send
from typing import Annotated
from typing import Any
from typing import Literal
from urllib.parse import quote

import hmac
import inspect
import json
import sys
import threading


Tool = Callable[..., Any]
Register = Callable[[Tool], Tool]

INSTRUCTIONS = """\
Work with the content of Plone 6 sites through plone.restapi.

Paths are site paths such as /news/my-item; the @id URLs that tools return
work too. Read the @id of what a tool creates: Plone may change the id that
was asked for.

Content model, mostly for sites with the Volto frontend:
- The text of a page is in its blocks: `blocks` maps block ids to block
  data and `blocks_layout.items` lists them in order; a page without both
  shows nothing. Use `block_types` to learn which blocks the site has and
  the data each one takes. To write prose, prefer `create_page`, which
  converts Markdown to blocks.
- Wherever a tool takes blocks, give them as a list in order, each with an
  `@type`; ids and the layout are made for you, and a container such as a
  gridBlock may list its own `blocks` the same way. To change a page,
  `list_blocks` shows its block ids; then `add_blocks`, `update_block` and
  `remove_blocks` change only those blocks.
- There is no Folder type: Document (Page) is folderish, and so is News Item.
- A News Item has no `image` field: its lead image is `preview_image_link`, a
  relation to an Image stored inside it. Use `create_content_with_files`.
- Fields a type does not have are silently ignored. Check the schema with
  `content_types` before setting unusual fields.
- New items are private until a workflow transition such as `publish` runs.

Changes are refused when the server is read-only. In a dry run, nothing is
changed: tools return the requests they would have sent.
"""

READ = ToolAnnotations(read_only_hint=True, open_world_hint=False)
CREATE = ToolAnnotations(
    read_only_hint=False, destructive_hint=False, open_world_hint=False
)
CHANGE = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=True,
    open_world_hint=False,
)
# A transition or a move fails when repeated, so a retry is not safe
ACTION = ToolAnnotations(
    read_only_hint=False,
    destructive_hint=True,
    idempotent_hint=False,
    open_world_hint=False,
)
DELETE = ToolAnnotations(
    read_only_hint=False, destructive_hint=True, open_world_hint=False
)

ItemPath = Annotated[
    str, Field(description="Site path, such as /news/item, or the item's @id URL.")
]
Folder = Annotated[str, Field(description="Path of the folder to create in.")]
Publish = Annotated[
    str | None,
    Field(description="Workflow transition to run at the end, such as publish."),
]
Data = Annotated[
    dict[str, Any] | None,
    Field(
        description="Field values, such as title, description or subjects. "
        "blocks may be a list of blocks in order, each with an @type."
    ),
]
BlocksChoice = Annotated[
    dict[str, bool | dict[str, Any]] | None,
    Field(
        description="Block types Markdown and HTML become, by @type: true or "
        "options to produce one, false to not, such as "
        '{"codeBlock": {"style": "light"}, "slateTable": false}. Merged over '
        "the site's setting, which the instructions give."
    ),
]
Blocks = Annotated[
    list[dict[str, Any]],
    Field(
        description="Blocks in order, each with an @type, such as "
        '{"@type": "teaser", "href": "/news/item"}. block_types describes '
        "the data of each block."
    ),
]


def tool_errors(func: Tool) -> Tool:
    """Report the errors of a tool to the model, as JSON.

    Unexpected exceptions reach the model only as "Error executing tool",
    so the errors a caller can act on are turned into ``ToolError``.

    :param func: The tool.
    :returns: The wrapped tool.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except PloneClientError as error:
            raise ToolError(json.dumps(error_payload(error))) from error
        except (ValueError, OSError) as error:
            details = {"type": error.__class__.__name__, "message": str(error)}
            raise ToolError(json.dumps({"error": details})) from error

    return wrapper


def resource_errors(func: Tool) -> Tool:
    """Report the errors of a resource to the client.

    Unexpected exceptions reach the client only as a generic error, so a
    missing item becomes the "resource not found" of the protocol, and the
    errors a caller can act on keep their message.

    :param func: The resource function.
    :returns: The wrapped function.
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except PloneNotFoundError as error:
            raise ResourceNotFoundError(str(error)) from error
        except (PloneClientError, ValueError, OSError) as error:
            raise ResourceError(str(error)) from error

    return wrapper


def _summary(item: dict[str, Any]) -> dict[str, Any]:
    """Short form of an item.

    :param item: A serialized item, or a dry run log entry.
    :returns: ``@id``, ``@type``, ``UID``, ``id``, ``title`` and
        ``review_state``; a dry run entry as it is.
    """
    if item.get("dry_run"):
        return item
    return {key: item[key] for key in operations.ITEM_KEYS if key in item}


def _project(item: dict[str, Any], fields: list[str] | None) -> dict[str, Any]:
    """Keep some keys of an item.

    :param item: The item.
    :param fields: Keys to keep; all when empty.
    :returns: The item.
    """
    if not fields:
        return item
    return {key: item[key] for key in fields if key in item}


@dataclass
class Site:
    """A site the server works on.

    :param name: Name the model picks it by: the profile name.
    :param url: URL of the site.
    :param description: What the site is, for the model.
    :param read_only: Whether changes to it are refused.
    :param factory: Builds its client, on first use.
    :param blocks: Block types that Markdown and HTML become on the site.
    :param lock: Held while a tool works on the site, one tool at a time: the
        client records the requests of an operation in one list, and block
        edits read and write the same item.
    """

    name: str
    url: str
    description: str = ""
    read_only: bool = False
    factory: Callable[[], PloneClient] | None = None
    client: PloneClient | None = None
    blocks: dict[str, Any] = field(default_factory=dict)
    lock: threading.Lock = field(
        default_factory=threading.Lock, repr=False, compare=False
    )

    def summary(self) -> dict[str, Any]:
        """The site, as ``list_sites`` reports it.

        :returns: ``name``, ``url``, ``description``, ``read_only`` and
            ``blocks``.
        """
        return {
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "read_only": self.read_only,
            "blocks": self.blocks,
        }


class Sites:
    """The sites of one server, each with a client created on first use.

    Creating a client looks up its secret, so a site whose secret is missing
    only fails when a tool uses it.

    :param sites: The sites, in the order the model sees them.
    :param dry_run: Whether the clients skip the requests that change a site.
    :raises ValueError: If there is no site, or two have the same name.
    """

    def __init__(self, sites: Iterable[Site], *, dry_run: bool = False) -> None:
        self._sites: dict[str, Site] = {}
        for site in sites:
            if site.name in self._sites:
                raise ValueError(f"Site {site.name!r} is given twice")
            self._sites[site.name] = site
        if not self._sites:
            raise ValueError("The server needs at least one site")
        self.dry_run = dry_run

    @classmethod
    def from_client(cls, client: PloneClient, name: str = "site") -> "Sites":
        """One site, served with a client that already exists.

        :param client: The client.
        :param name: Name of the site.
        :returns: The sites.
        """
        site = Site(
            name,
            client.url,
            read_only=client.read_only,
            client=client,
            blocks=dict(client.blocks),
        )
        return cls([site], dry_run=client.dry_run)

    @classmethod
    def from_profiles(
        cls,
        profiles: Iterable[Profile],
        *,
        read_only: bool = False,
        dry_run: bool = False,
        factory: Callable[..., PloneClient] = PloneClient,
    ) -> "Sites":
        """Sites for profiles.

        :param profiles: The profiles.
        :param read_only: Refuse changes to every site, whatever its profile.
        :param dry_run: Skip the requests that change a site.
        :param factory: Builds a client from keyword arguments.
        :returns: The sites.
        """

        def builder(profile: Profile, read_only: bool) -> Callable[[], PloneClient]:
            def build() -> PloneClient:
                settings = profile.client_settings()
                settings.update(read_only=read_only, dry_run=dry_run)
                return factory(**settings)

            return build

        sites = []
        for profile in profiles:
            locked = read_only or profile.read_only
            sites.append(
                Site(
                    profile.name,
                    profile.url,
                    description=profile.description,
                    read_only=locked,
                    factory=builder(profile, locked),
                    blocks=dict(profile.blocks),
                )
            )
        return cls(sites, dry_run=dry_run)

    @property
    def names(self) -> list[str]:
        """Names of the sites, in order."""
        return list(self._sites)

    @property
    def multiple(self) -> bool:
        """Whether there is more than one site."""
        return len(self._sites) > 1

    @property
    def writable(self) -> bool:
        """Whether at least one site accepts changes."""
        return any(not site.read_only for site in self._sites.values())

    def __iter__(self) -> Iterator[Site]:
        return iter(self._sites.values())

    def site(self, name: str | None = None) -> Site:
        """A site, by name.

        :param name: Site name; the only site when there is one.
        :returns: The site.
        :raises PloneConfigurationError: If the site is unknown.
        """
        if name is None and not self.multiple:
            name = self.names[0]
        site = self._sites.get(name or "")
        if site is None:
            raise PloneConfigurationError(
                f"Unknown site {name!r} (known: {', '.join(self.names)})"
            )
        return site

    def client(self, name: str | None = None) -> PloneClient:
        """The client of a site, created on first use.

        :param name: Site name; the only site when there is one.
        :returns: The client.
        :raises PloneConfigurationError: If the site is unknown, or its
            secret cannot be found.
        """
        site = self.site(name)
        if site.client is None:
            if site.factory is None:  # no cov
                raise PloneConfigurationError(f"Site {name!r} has no client")
            site.client = site.factory()
        return site.client

    def close(self) -> None:
        """Close the clients that were created."""
        for site in self._sites.values():
            if site.client is not None:
                site.client.close()
                site.client = None


def rejected_sites(sites: Sites) -> list[str]:
    """Names of the sites whose credentials the site rejects.

    Connects to each site once, at startup. A site that cannot be reached, or
    whose secret cannot be found, is left out: its tools report that when used.

    :param sites: The sites.
    :returns: Names of the sites, in order.
    """
    from .cli.profile import check_connection

    names = []
    for site in sites:
        try:
            client = sites.client(site.name)
            report = check_connection(client, client.username)
        except PloneClientError:
            continue
        if report["credentials_rejected"]:
            names.append(site.name)
    return names


def _instructions(sites: Sites, rejected: tuple[str, ...] = ()) -> str:
    """Instructions for the model, with the sites and their modes.

    :param sites: The sites.
    :param rejected: Names of the sites whose credentials were rejected.
    :returns: The instructions.
    """
    lines = [INSTRUCTIONS]
    if sites.multiple:
        lines.append(
            "This server works on several sites. Every tool takes a `site` "
            "argument; `list_sites` describes them:"
        )
        for site in sites:
            mode = " (read-only)" if site.read_only else ""
            about = f": {site.description}" if site.description else ""
            lines.append(f"- `{site.name}`, {site.url}{mode}{about}")
        lines.append("")
    elif not sites.writable:
        lines.append("This server is read-only.\n")
    for site in sites:
        if site.blocks:
            where = f" on `{site.name}`" if sites.multiple else ""
            lines.append(
                f"Markdown and HTML{where} become blocks with this setting, which "
                f"a tool's `blocks` argument extends: {json.dumps(site.blocks)}\n"
            )
    if sites.dry_run:
        lines.append("This server is in a dry run.\n")
    for name in rejected:
        lines.append(
            f"Warning: the credentials of `{name}` were rejected. The site answers "
            "as anonymous, so reads show only public content and changes fail. "
            f"Ask the user to run `plone-client profile set-secret {name}`.\n"
        )
    return "\n".join(lines)


def _per_site(sites: Sites, func: Tool) -> Tool:
    """A tool that gets the client of a site in place of its first parameter.

    The tool's first parameter is ``client``. With one site, the model never
    sees it; with several, it becomes a required ``site`` argument whose
    values are the names of the sites.

    :param sites: The sites.
    :param func: The tool.
    :returns: The tool as the server offers it.
    """
    signature = inspect.signature(func)
    parameters = list(signature.parameters.values())[1:]
    if sites.multiple:
        names = tuple(sites.names)
        site = inspect.Parameter(
            "site",
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            annotation=Annotated[
                Literal[names],
                Field(description="Site to work on; list_sites describes them."),
            ],
        )
        parameters.insert(0, site)

    @wraps(func)
    def wrapper(**kwargs: Any) -> Any:
        # The SDK runs tools in worker threads, so calls can overlap
        site = sites.site(kwargs.pop("site", None))
        with site.lock:
            return func(sites.client(site.name), **kwargs)

    wrapper.__signature__ = signature.replace(  # type: ignore[attr-defined]
        parameters=parameters
    )
    return wrapper


def has_html2blocks() -> bool:
    """Whether ``collective.html2blocks`` is installed.

    :returns: ``True`` if it can be imported.
    """
    try:
        return find_spec("collective.html2blocks") is not None
    except ModuleNotFoundError:
        # find_spec imports the parent package, which may be missing too
        return False


def build_server(
    target: PloneClient | Sites,
    rejected: tuple[str, ...] = (),
    tools: Iterable[str] | None = None,
) -> MCPServer:
    """An MCP server whose tools work on one site or several.

    :param target: A client, for one site, or the sites. Each client's
        ``read_only`` and ``dry_run`` settings apply to its tools.
    :param rejected: Names of the sites whose credentials were rejected, for
        the instructions.
    :param tools: Names of the only tools to offer, to keep the list the
        model reads short; all when ``None``. ``list_sites`` is offered with
        several sites either way.
        A resource is offered only when the tool that reads the same data is.
    :returns: The server, ready to ``run()``.
    :raises PloneConfigurationError: If a tool in ``tools`` is not one this
        server offers, such as a tool that changes a read-only site.
    """
    wanted = None if tools is None else set(tools)
    known: list[str] = []
    sites = target if isinstance(target, Sites) else Sites.from_client(target)
    title = (
        f"Plone sites {', '.join(sites.names)}"
        if sites.multiple
        else f"Plone site {next(iter(sites)).url}"
    )
    server = MCPServer(
        name="plone-client",
        title=title,
        instructions=_instructions(sites, rejected),
        version=__version__,
        # INFO would log every HTTP request; -v still logs plone_client's
        log_level="WARNING",
    )

    def add(annotations: ToolAnnotations) -> Register:
        def decorator(func: Tool) -> Tool:
            known.append(func.__name__)
            if wanted is not None and func.__name__ not in wanted:
                return func
            server.add_tool(
                tool_errors(_per_site(sites, func)),
                name=func.__name__,
                annotations=annotations,
            )
            return func

        return decorator

    if sites.multiple:

        def list_sites() -> dict[str, Any]:
            """The sites this server works on: name, URL, description, and
            whether changes to it are refused.

            Pass the name as the site argument of the other tools.
            """
            return {"items": [site.summary() for site in sites]}

        server.add_tool(list_sites, annotations=READ)
    _read_tools(add(READ), add(ACTION))
    _block_tools(add, sites.writable)
    _workflow_tools(add)
    _translation_tools(add, sites.writable)
    _working_copy_tools(add, sites.writable)
    if sites.writable:
        _write_tools(add)
        _operation_tools(add)
    unknown = sorted((wanted or set()) - set(known))
    if unknown:
        raise PloneConfigurationError(
            f"This server does not offer {', '.join(unknown)} "
            f"(it offers: {', '.join(sorted(known))})"
        )
    for site in sites:
        _site_resources(_resource_register(server, sites, site, wanted))
    return server


def _resource_register(
    server: MCPServer, sites: Sites, site: Site, wanted: set[str] | None
) -> Callable[..., Register]:
    """A decorator factory that adds resources of one site to the server.

    Every site has its own URIs, ``plone://<site>/...``, so a client can tell
    them apart, and a site the server does not know is not found.

    :param server: The server.
    :param sites: The sites of the server.
    :param site: The site.
    :param wanted: Names of the only tools to offer, or ``None``.
    :returns: The factory.
    """
    root = f"plone://{quote(site.name, safe='')}"

    def resource(
        tool: str, path: str, title: str, mime_type: str = "application/json"
    ) -> Register:
        """Register a function of a client as a resource, if ``tool`` is offered.

        :param tool: The tool that reads the same data.
        :param path: Path of the URI, a template when it has variables.
        :param title: Title of the resource.
        :param mime_type: Media type of the result.
        :returns: The decorator.
        """

        def decorator(func: Tool) -> Tool:
            if wanted is not None and tool not in wanted:
                return func
            signature = inspect.signature(func)
            parameters = list(signature.parameters.values())[1:]

            @wraps(func)
            def wrapper(**kwargs: Any) -> Any:
                with site.lock:
                    return func(sites.client(site.name), **kwargs)

            wrapper.__signature__ = signature.replace(  # type: ignore[attr-defined]
                parameters=parameters
            )
            server.resource(
                f"{root}{path}",
                name=f"{site.name}-{func.__name__}",
                title=f"{site.name}: {title}",
                mime_type=mime_type,
            )(resource_errors(wrapper))
            return func

        return decorator

    return resource


def _site_resources(resource: Callable[..., Register]) -> None:
    """Add the resources of one site.

    :param resource: See :func:`_resource_register`.
    """

    @resource("get_content", "/site", "Site root")
    def site_root(client: PloneClient) -> dict[str, Any]:
        """The root of the site, as the API serializes it."""
        return client.content.get("/")

    @resource("get_content", "/content/{+path}", "Content item")
    def content_item(client: PloneClient, path: str) -> dict[str, Any]:
        """The full JSON of a content item, by its path in the site."""
        return client.content.get(f"/{path}")

    @resource("content_types", "/types", "Content types")
    def type_list(client: PloneClient) -> list[dict[str, Any]]:
        """The content types of the site."""
        return client.types.list()

    @resource("content_types", "/types/{portal_type}", "Content type schema")
    def type_schema(client: PloneClient, portal_type: str) -> dict[str, Any]:
        """The JSON schema of a content type."""
        return client.types.get(portal_type)

    @resource("block_types", "/blocks", "Blocks", "text/markdown")
    def block_list(client: PloneClient) -> str:
        """The blocks the site offers, with a summary of each."""
        return client.block_types.markdown()

    @resource("block_types", "/blocks/{block_id}", "Block", "text/markdown")
    def block_docs(client: PloneClient, block_id: str) -> str:
        """The documentation, data schema and variations of a block."""
        return client.block_types.markdown(block_id)


def _read_tools(read: Register, action: Register) -> None:
    """Register the tools that only read, and the generic service tool.

    :param read: Registers a read-only tool.
    :param action: Registers a tool that may change the site.
    """

    @read
    def site_info(client: PloneClient) -> dict[str, Any]:
        """The site, the user the server is logged in as, and its mode.

        Call this first to check the connection.
        """
        from .cli.profile import check_connection

        return {
            **check_connection(client, client.username),
            "frontend_url": client.frontend_url,
            "dry_run": client.dry_run,
        }

    @read
    def get_content(
        client: PloneClient,
        path: ItemPath = "/",
        fields: Annotated[
            list[str] | None,
            Field(
                description="Keys to return, such as ['title', 'blocks']; all if empty."
            ),
        ] = None,
        expand: Annotated[
            list[str] | None,
            Field(description="Components to expand: breadcrumbs, translations…"),
        ] = None,
    ) -> dict[str, Any]:
        """Read one content item: its fields, blocks and workflow state.

        Contained items are left out; use list_children for them.
        """
        item = client.content.get(path, expand=expand, include_items=False)
        return _project(item, fields)

    @read
    def list_children(
        client: PloneClient,
        path: ItemPath = "/",
        portal_type: Annotated[
            list[str] | None, Field(description="Only items of these types.")
        ] = None,
        limit: Annotated[int, Field(ge=1, le=500)] = 50,
    ) -> dict[str, Any]:
        """List the items directly inside a folder, in the folder's order."""
        items = list(
            client.content.children(path, portal_type=portal_type, limit=limit)
        )
        return {"items": items, "items_count": len(items)}

    @read
    def search(
        client: PloneClient,
        path: ItemPath = "/",
        text: Annotated[str | None, Field(description="Full-text search.")] = None,
        portal_type: Annotated[
            list[str] | None, Field(description="Content types.")
        ] = None,
        review_state: Annotated[
            list[str] | None, Field(description="Workflow states, such as published.")
        ] = None,
        depth: Annotated[
            int | None,
            Field(description="Levels below path: 1 for direct children."),
        ] = None,
        query: Annotated[
            dict[str, Any] | None,
            Field(
                description="Other catalog indexes, such as "
                '{"Subject": "news"} or {"modified": {"query": "2026-01-01", '
                '"range": "min"}}.'
            ),
        ] = None,
        sort_on: Annotated[
            str | None, Field(description="Index to sort on, such as modified.")
        ] = None,
        descending: bool = False,
        limit: Annotated[int, Field(ge=1, le=500)] = 25,
    ) -> dict[str, Any]:
        """Search the catalog of the site, inside a folder."""
        items = list(
            client.search.iter(
                client.content.resolve(path),
                query=query,
                portal_type=portal_type,
                review_state=review_state,
                text=text,
                depth=depth,
                sort_on=sort_on,
                sort_order="descending" if descending else None,
                limit=limit,
                b_size=min(limit, 100),
            )
        )
        return {"items": items, "items_count": len(items)}

    @read
    def get_navigation(
        client: PloneClient,
        path: ItemPath = "/",
        depth: Annotated[int, Field(ge=1, le=5)] = 2,
    ) -> dict[str, Any]:
        """The navigation tree of the site, to find where content lives."""
        return client.navigation.navigation(path, depth=depth)

    @read
    def content_types(
        client: PloneClient,
        portal_type: Annotated[
            str | None,
            Field(description="Type whose JSON schema to return, such as Document."),
        ] = None,
        addable_in: Annotated[
            str | None,
            Field(description="Only the types that can be added in this folder."),
        ] = None,
    ) -> dict[str, Any]:
        """List the content types, or return the field schema of one."""
        if portal_type:
            return client.types.get(portal_type)
        items = [
            {
                "id": entry["@id"].rsplit("/", 1)[-1],
                "title": entry.get("title"),
                "addable": entry.get("addable"),
            }
            for entry in client.types.list(addable_in or "/")
            if entry.get("addable") or not addable_in
        ]
        return {"items": items}

    @read
    def block_types(
        client: PloneClient,
        block_id: Annotated[
            str | None,
            Field(description="Block whose docs and data schema to return."),
        ] = None,
        path: Annotated[
            str | None,
            Field(description="Only the blocks that can be added to this item."),
        ] = None,
    ) -> str:
        """The blocks the site offers, or how to write the data of one block.

        Returns Markdown: without block_id, a list of blocks with a summary;
        with it, the block's documentation, data schema and variations.
        """
        return client.block_types.markdown(block_id, path)

    @action
    def call_service(
        client: PloneClient,
        method: Literal["GET", "POST", "PATCH", "PUT", "DELETE"],
        path: Annotated[
            str,
            Field(description="Path with the service, such as /news/@workflow."),
        ],
        params: Annotated[
            dict[str, Any] | None, Field(description="Query parameters.")
        ] = None,
        body: Annotated[Any, Field(description="JSON body.")] = None,
    ) -> dict[str, Any]:
        """Call any plone.restapi service that no other tool covers.

        Requests that change the site follow the server's read-only and dry run
        settings.
        """
        response = client.request(method, path, params=params, json=body)
        answer = response.json() if response.content else None
        return {"status": response.status_code, "body": answer}


def _write_tools(add: Callable[[ToolAnnotations], Register]) -> None:
    """Register the tools that change the site.

    :param add: Registers a tool with its annotations.
    """

    @add(CREATE)
    def create_content(
        client: PloneClient,
        parent: Folder,
        portal_type: Annotated[
            str, Field(description="Content type, such as Document.")
        ],
        data: Data = None,
        publish: Publish = None,
    ) -> dict[str, Any]:
        """Create one content item with the given field values.

        For pages written in Markdown use create_page, and for items with
        images use create_content_with_files.
        """
        item = client.content.create(parent, portal_type, blocks.prepare(data or {}))
        if publish and not client.dry_run:
            client.workflow.transition(item["@id"], publish)
            item = client.content.get(item["@id"], include_items=False)
        return _summary(item)

    @add(CHANGE)
    def update_content(
        client: PloneClient, path: ItemPath, data: Data
    ) -> dict[str, Any]:
        """Change field values of a content item; other fields are kept.

        Giving blocks replaces all of them; to change some, use add_blocks,
        update_block or remove_blocks.
        """
        item = client.content.update(path, blocks.prepare(data or {}))
        return _summary(item or {})

    @add(ACTION)
    def run_transition(
        client: PloneClient,
        path: ItemPath,
        transition: Annotated[
            str, Field(description="Transition id, such as publish or retract.")
        ],
        comment: str | None = None,
        include_children: bool = False,
    ) -> dict[str, Any]:
        """Run a workflow transition, such as publish, on a content item."""
        return client.workflow.transition(
            path, transition, comment=comment, include_children=include_children
        )

    @add(DELETE)
    def delete_content(
        client: PloneClient,
        paths: Annotated[list[str], Field(description="Items to delete.")],
    ) -> dict[str, Any]:
        """Delete content items, and everything inside them."""
        deleted = []
        for ref in paths:
            path = client.content.resolve(ref)
            client.content.delete(path)
            deleted.append(path)
        return {"deleted": deleted, "dry_run": client.dry_run}


def _operation_tools(add: Callable[[ToolAnnotations], Register]) -> None:
    """Register the high-level operations, which group several requests.

    :param add: Registers a tool with its annotations.
    """

    @add(CREATE)
    def create_content_with_files(
        client: PloneClient,
        parent: Folder,
        portal_type: Annotated[
            str, Field(description="Content type, such as News Item.")
        ],
        files: Annotated[
            list[str], Field(description="Local paths of files and images to upload.")
        ],
        data: Data = None,
        lead_image: Annotated[
            int | Literal["first"] | None,
            Field(
                description="Index in files of the lead image, 'first' for the "
                "first image, or null for none."
            ),
        ] = "first",
        publish: Publish = None,
    ) -> dict[str, Any]:
        """Create an item, upload files and images inside it, and set its lead image.

        The lead image is stored the way the type expects: in its image field,
        or as an Image inside the item that preview_image_link points to (News
        Items on Volto sites). Returns everything created and every request.
        """
        result = operations.create_with_files(
            client,
            parent,
            portal_type,
            files,
            data=data,
            lead_image=lead_image,
            publish=publish,
        )
        return result.to_dict()

    if has_html2blocks():

        @add(CREATE)
        def create_page(
            client: PloneClient,
            parent: Folder,
            source: Annotated[str, Field(description="Markdown or HTML text.")],
            source_format: Literal["markdown", "html"] = "markdown",
            portal_type: Annotated[
                str,
                Field(
                    description="Content type, with blocks. Use content_types to "
                    "list the types addable in a folder."
                ),
            ] = "Document",
            title: Annotated[
                str | None,
                Field(description="Title; the leading # heading by default."),
            ] = None,
            description: str | None = None,
            data: Data = None,
            files: Annotated[
                list[str] | None,
                Field(description="Local paths of files and images to upload."),
            ] = None,
            lead_image: Annotated[
                int | Literal["first"] | None,
                Field(
                    description="Index in files of the lead image, 'first' for the "
                    "first image, or null for none."
                ),
            ] = "first",
            publish: Publish = None,
            blocks: BlocksChoice = None,
        ) -> dict[str, Any]:
            """Create a page from Markdown or HTML, converted to Volto blocks.

            Headings, paragraphs, lists, quotes, links, images and tables
            become blocks. The page also gets title and description blocks.
            Files are uploaded inside the page, and the lead image is stored
            the way the type expects, as create_content_with_files does. The
            type must have blocks.
            """
            result = operations.create_page(
                client,
                parent,
                source,
                source_format=source_format,
                portal_type=portal_type,
                title=title,
                description=description,
                data=data,
                files=files or (),
                lead_image=lead_image,
                publish=publish,
                blocks_setting=blocks,
            )
            return result.to_dict()

    @add(CREATE)
    def upload_tree(
        client: PloneClient,
        local_path: Annotated[str, Field(description="Local folder to upload.")],
        parent: Annotated[
            str, Field(description="Folder of the site that receives its contents.")
        ],
        convert_pages: Annotated[
            bool,
            Field(description="Turn Markdown and HTML files into pages."),
        ] = False,
        publish: Publish = None,
        blocks: BlocksChoice = None,
    ) -> dict[str, Any]:
        """Upload a local folder: subfolders become pages, files become File
        and Image items, keeping the structure.
        """
        result = operations.upload_tree(
            client,
            local_path,
            parent,
            convert_pages=convert_pages,
            publish=publish,
            blocks_setting=blocks,
        )
        return result.to_dict()

    @add(CREATE)
    def copy_content(
        client: PloneClient,
        sources: Annotated[list[str], Field(description="Items to copy.")],
        target: Annotated[str, Field(description="Folder to copy into.")],
    ) -> dict[str, Any]:
        """Copy items, with everything inside them, into a folder.

        Reports where each copy went and how many items it holds.
        """
        return operations.copy_items(client, sources, target).to_dict()

    @add(ACTION)
    def move_content(
        client: PloneClient,
        sources: Annotated[list[str], Field(description="Items to move.")],
        target: Annotated[str, Field(description="Folder to move into.")],
    ) -> dict[str, Any]:
        """Move items, with everything inside them, into a folder.

        Their URLs change; Plone redirects the old ones.
        """
        return operations.move_items(client, sources, target).to_dict()


def _block_tools(add: Callable[[ToolAnnotations], Register], writable: bool) -> None:
    """Register the tools that read and change the blocks of an item.

    :param add: Registers a tool with its annotations.
    :param writable: Whether to register the tools that change blocks.
    """

    @add(READ)
    def list_blocks(client: PloneClient, path: ItemPath) -> dict[str, Any]:
        """The blocks of an item, in order: id, type and the start of their
        text, with the blocks inside containers.

        Use the ids with add_blocks, update_block and remove_blocks; read a
        block's full data with get_content and fields ['blocks'].
        """
        item = client.content.get(path, include_items=False)
        return {
            "@id": item["@id"],
            "blocks": blocks.outline(item.get("blocks"), item.get("blocks_layout")),
        }

    if not writable:
        return

    @add(CREATE)
    def add_blocks(
        client: PloneClient,
        path: ItemPath,
        items: Blocks,
        after: Annotated[
            str | None,
            Field(
                description="Id of the block to add them after, in the same "
                "container; list_blocks shows the ids."
            ),
        ] = None,
        position: Annotated[
            int | None,
            Field(ge=0, description="Index among the item's blocks; 0 is the top."),
        ] = None,
    ) -> dict[str, Any]:
        """Add blocks to an item, keeping the blocks it has.

        They go after the block given, at the position given, or at the end.
        Returns the new block ids and an outline of the item's blocks.
        """
        return operations.add_blocks(
            client, path, items, after=after, position=position
        ).to_dict()

    @add(CHANGE)
    def update_block(
        client: PloneClient,
        path: ItemPath,
        block_id: Annotated[str, Field(description="Id of the block.")],
        data: Annotated[
            dict[str, Any], Field(description="Values to merge into the block.")
        ],
        replace: Annotated[
            bool,
            Field(description="Replace the block's data instead of merging."),
        ] = False,
    ) -> dict[str, Any]:
        """Change the data of one block, also inside a container."""
        return operations.update_block(
            client, path, block_id, data, replace=replace
        ).to_dict()

    @add(DELETE)
    def remove_blocks(
        client: PloneClient,
        path: ItemPath,
        block_ids: Annotated[list[str], Field(description="Ids of the blocks.")],
    ) -> dict[str, Any]:
        """Remove blocks from an item, with any blocks inside them."""
        return operations.remove_blocks(client, path, block_ids).to_dict()

    @add(CHANGE)
    def set_blocks(
        client: PloneClient, path: ItemPath, items: Blocks
    ) -> dict[str, Any]:
        """Replace all the blocks of an item.

        Its title and description blocks stay at the top unless the new
        blocks include blocks of those types.
        """
        return operations.set_blocks(client, path, items).to_dict()


def _workflow_tools(add: Callable[[ToolAnnotations], Register]) -> None:
    """Register the tools for workflow transitions and vocabularies.

    :param add: Registers a tool with its annotations.
    """

    @add(READ)
    def get_workflow(client: PloneClient, path: ItemPath) -> dict[str, Any]:
        """The workflow state of an item and the transitions it can run now.

        Pass a transition id to run_transition.
        """
        found = client.workflow.get(path)
        return {
            "state": found.get("state"),
            "transitions": [
                {"id": entry["@id"].rsplit("/", 1)[-1], "title": entry.get("title")}
                for entry in found.get("transitions") or []
            ],
        }

    @add(READ)
    def get_vocabulary(
        client: PloneClient,
        vocabulary: Annotated[
            str | None,
            Field(
                description="Vocabulary, such as plone.app.vocabularies.Keywords; "
                "without it, the vocabularies of the site."
            ),
        ] = None,
        path: Annotated[
            str, Field(description="Item whose context the vocabulary uses.")
        ] = "/",
        title: Annotated[
            str | None, Field(description="Only terms whose title contains this.")
        ] = None,
        limit: Annotated[int, Field(ge=1, le=500)] = 50,
    ) -> dict[str, Any]:
        """The valid values of a choice field: the terms of a vocabulary.

        content_types shows which vocabulary a field uses. Store a term's
        token in the field.
        """
        if not vocabulary:
            return {"items": client.vocabularies.list(path)}
        found = client.vocabularies.get(vocabulary, ref=path, title=title, b_size=limit)
        return {
            "items": found.get("items", []),
            "items_total": found.get("items_total"),
        }


def _translation_tools(
    add: Callable[[ToolAnnotations], Register], writable: bool
) -> None:
    """Register the tools for translations.

    :param add: Registers a tool with its annotations.
    :param writable: Whether to register the tools that change the site.
    """

    @add(READ)
    def get_translations(client: PloneClient, path: ItemPath) -> dict[str, Any]:
        """The translations linked to an item, with their language.

        Needs plone.app.multilingual on the site.
        """
        return client.translations.get(path)

    if not writable:
        return

    @add(CREATE)
    def link_translation(
        client: PloneClient,
        path: ItemPath,
        translation: Annotated[
            str, Field(description="Path, URL or UID of the existing translation.")
        ],
    ) -> dict[str, Any]:
        """Link an existing item as a translation of another."""
        return client.translations.link(path, translation)

    @add(DELETE)
    def unlink_translation(
        client: PloneClient,
        path: ItemPath,
        language: Annotated[str, Field(description="Language code, such as de.")],
    ) -> dict[str, Any]:
        """Remove the link to the translation in a language; both items stay."""
        client.translations.unlink(path, language)
        return {"unlinked": language, "dry_run": client.dry_run}


def _working_copy_tools(
    add: Callable[[ToolAnnotations], Register], writable: bool
) -> None:
    """Register the tools for working copies.

    :param add: Registers a tool with its annotations.
    :param writable: Whether to register the tools that change the site.
    """

    @add(READ)
    def get_working_copy(client: PloneClient, path: ItemPath) -> dict[str, Any]:
        """The working copy of an item, or the item a working copy belongs to.

        Needs plone.app.iterate on the site.
        """
        return client.working_copy.get(path)

    if not writable:
        return

    @add(CREATE)
    def check_out(client: PloneClient, path: ItemPath) -> dict[str, Any]:
        """Check out an item into a working copy, to change a published item
        without changing what visitors see.

        Change the working copy, then check_in to apply it.
        """
        return client.working_copy.create(path)

    @add(ACTION)
    def check_in(
        client: PloneClient,
        path: Annotated[
            str, Field(description="Path of the working copy, or of its item.")
        ],
    ) -> dict[str, Any]:
        """Apply a working copy to its item, and remove the working copy."""
        client.working_copy.check_in(path)
        return {"checked_in": path, "dry_run": client.dry_run}

    @add(DELETE)
    def cancel_working_copy(
        client: PloneClient,
        path: Annotated[
            str, Field(description="Path of the working copy, or of its item.")
        ],
    ) -> dict[str, Any]:
        """Remove a working copy without applying it."""
        client.working_copy.delete(path)
        return {"cancelled": path, "dry_run": client.dry_run}


@dataclass
class HTTPSettings:
    """How the server listens over HTTP.

    :param token: Token that clients send as ``Authorization: Bearer``.
    :param host: Address to listen on. Other hosts than the loopback should
        be reached through a proxy that adds TLS.
    :param port: Port to listen on.
    :param path: Path of the MCP endpoint.
    """

    token: str
    host: str = "127.0.0.1"
    port: int = 8000
    path: str = "/mcp"


class BearerToken:
    """ASGI middleware that answers 401 to HTTP requests without the token.

    The token is compared in constant time. Other ASGI scopes, such as the
    lifespan, pass through.

    :param app: The application to protect.
    :param token: The token clients must send.
    """

    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self.token = token.encode()

    def authorized(self, scope: Scope) -> bool:
        """Whether a request carries the token.

        :param scope: The ASGI scope of the request.
        :returns: ``True`` for ``Authorization: Bearer <token>``.
        """
        headers = dict(scope.get("headers") or [])
        scheme, _, given = headers.get(b"authorization", b"").partition(b" ")
        return scheme.lower() == b"bearer" and hmac.compare_digest(
            given.strip(), self.token
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and not self.authorized(scope):
            response = JSONResponse(
                {"error": "A valid bearer token is required"},
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer realm="plone-client"'},
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)


def http_app(server: MCPServer, settings: HTTPSettings) -> ASGIApp:
    """The server as an ASGI application that requires the token.

    :param server: The server, from :func:`build_server`.
    :param settings: Where it listens, and its token.
    :returns: The application.
    """
    app = server.streamable_http_app(
        streamable_http_path=settings.path, host=settings.host
    )
    return BearerToken(app, settings.token)


def serve(
    target: PloneClient | Sites,
    tools: Iterable[str] | None = None,
    http: HTTPSettings | None = None,
) -> None:
    """Serve the tools over standard input and output, or over HTTP.

    :param target: A client, for one site, or the sites; their clients are
        closed when the server stops.
    :param tools: Names of the only tools to offer; see :func:`build_server`.
    :param http: Serve over streamable HTTP with these settings, instead of
        standard input and output.
    :raises PloneConfigurationError: If a tool in ``tools`` is not offered.
    """
    from .cli.profile import rejected_message

    sites = target if isinstance(target, Sites) else Sites.from_client(target)
    try:
        if tools is not None:
            # Refuse an unknown tool before connecting to the sites
            build_server(sites, tools=tools)
        rejected = tuple(rejected_sites(sites))
        for name in rejected:
            sys.stderr.write(f"plone-client: warning: {rejected_message(name)}\n")
        server = build_server(sites, rejected, tools)
        if http is None:
            server.run("stdio")
            return
        import uvicorn

        sys.stderr.write(
            f"plone-client: serving MCP at http://{http.host}:{http.port}{http.path}\n"
        )
        uvicorn.run(
            http_app(server, http), host=http.host, port=http.port, log_level="warning"
        )
    finally:
        sites.close()
