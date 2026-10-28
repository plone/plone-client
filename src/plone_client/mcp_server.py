"""An MCP server for Plone sites, built on the client and its operations.

The server gives chat assistants and agents without a shell the same access
the command line gives: the same profiles, secrets in the keyring, and the
same ``read_only`` and ``dry_run`` switches. It speaks over standard input
and output, for one site or several::

    pip install 'plone-client[mcp]'
    plone-client mcp --profile blog
    plone-client mcp --site blog --site docs
    plone-client mcp --group customer
    plone-client mcp --all

Rather than one tool per ``plone.restapi`` service, it offers the everyday
reads, the high-level operations of :mod:`plone_client.operations`, and one
tool for any other service. With several sites, every tool takes a ``site``
argument, and ``list_sites`` describes them. Tools that change a site are
only offered when at least one site accepts changes; a change to a read-only
site is refused before it is sent.
"""

from . import __version__
from . import operations
from .client import PloneClient
from .exceptions import error_payload
from .exceptions import PloneClientError
from .exceptions import PloneConfigurationError
from .profiles import Profile
from collections.abc import Callable
from collections.abc import Iterable
from collections.abc import Iterator
from dataclasses import dataclass
from functools import wraps
from importlib.util import find_spec
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field
from typing import Annotated
from typing import Any
from typing import Literal

import inspect
import json


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
    Field(description="Field values, such as title, description or subjects."),
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
    """

    name: str
    url: str
    description: str = ""
    read_only: bool = False
    factory: Callable[[], PloneClient] | None = None
    client: PloneClient | None = None

    def summary(self) -> dict[str, Any]:
        """The site, as ``list_sites`` reports it.

        :returns: ``name``, ``url``, ``description`` and ``read_only``.
        """
        return {
            "name": self.name,
            "url": self.url,
            "description": self.description,
            "read_only": self.read_only,
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
        site = Site(name, client.url, read_only=client.read_only, client=client)
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

    def client(self, name: str | None = None) -> PloneClient:
        """The client of a site, created on first use.

        :param name: Site name; the only site when there is one.
        :returns: The client.
        :raises PloneConfigurationError: If the site is unknown, or its
            secret cannot be found.
        """
        if name is None and not self.multiple:
            name = self.names[0]
        site = self._sites.get(name or "")
        if site is None:
            raise PloneConfigurationError(
                f"Unknown site {name!r} (known: {', '.join(self.names)})"
            )
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


def _instructions(sites: Sites) -> str:
    """Instructions for the model, with the sites and their modes.

    :param sites: The sites.
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
    if sites.dry_run:
        lines.append("This server is in a dry run.\n")
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
        return func(sites.client(kwargs.pop("site", None)), **kwargs)

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


def build_server(target: PloneClient | Sites) -> MCPServer:
    """An MCP server whose tools work on one site or several.

    :param target: A client, for one site, or the sites. Each client's
        ``read_only`` and ``dry_run`` settings apply to its tools.
    :returns: The server, ready to ``run()``.
    """
    sites = target if isinstance(target, Sites) else Sites.from_client(target)
    title = (
        f"Plone sites {', '.join(sites.names)}"
        if sites.multiple
        else f"Plone site {next(iter(sites)).url}"
    )
    server = MCPServer(
        name="plone-client",
        title=title,
        instructions=_instructions(sites),
        version=__version__,
        # INFO would log every HTTP request; -v still logs plone_client's
        log_level="WARNING",
    )

    def add(annotations: ToolAnnotations) -> Register:
        def decorator(func: Tool) -> Tool:
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
    _read_tools(add(READ), add(CHANGE))
    if sites.writable:
        _write_tools(add)
        _operation_tools(add)
    return server


def _read_tools(read: Register, change: Register) -> None:
    """Register the tools that only read, and the generic service tool.

    :param read: Registers a read-only tool.
    :param change: Registers a tool that may change the site.
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

    @change
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
        item = client.content.create(parent, portal_type, data or {})
        if publish and not client.dry_run:
            client.workflow.transition(item["@id"], publish)
            item = client.content.get(item["@id"], include_items=False)
        return _summary(item)

    @add(CHANGE)
    def update_content(
        client: PloneClient, path: ItemPath, data: Data
    ) -> dict[str, Any]:
        """Change field values of a content item; other fields are kept."""
        item = client.content.update(path, data or {})
        return _summary(item or {})

    @add(CHANGE)
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
    ) -> dict[str, Any]:
        """Upload a local folder: subfolders become pages, files become File
        and Image items, keeping the structure.
        """
        result = operations.upload_tree(
            client, local_path, parent, convert_pages=convert_pages, publish=publish
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

    @add(CHANGE)
    def move_content(
        client: PloneClient,
        sources: Annotated[list[str], Field(description="Items to move.")],
        target: Annotated[str, Field(description="Folder to move into.")],
    ) -> dict[str, Any]:
        """Move items, with everything inside them, into a folder.

        Their URLs change; Plone redirects the old ones.
        """
        return operations.move_items(client, sources, target).to_dict()


def serve(target: PloneClient | Sites) -> None:
    """Serve the tools over standard input and output.

    :param target: A client, for one site, or the sites; their clients are
        closed when the server stops.
    """
    sites = target if isinstance(target, Sites) else Sites.from_client(target)
    try:
        build_server(sites).run("stdio")
    finally:
        sites.close()
