"""High-level operations: tasks that take several requests, in the right order.

Each operation gets a task right on any Plone 6 site, Volto sites included,
where doing it request by request means knowing the content model: a News
Item has no ``image`` field there, and its lead image is a relation to an
Image stored inside it.

Every operation returns an :class:`OperationResult` that lists what it
created or changed and every request it sent. With a ``dry_run`` client,
nothing is sent: the result shows the planned requests, with the paths the
new items would most likely get. A read-only client refuses the first
change. When a request fails part way, the operation raises
:class:`~plone_client.exceptions.PloneOperationError`, whose ``result`` lists
what was already done, so the caller can clean up or resume.

Example::

    from plone_client import PloneClient
    from plone_client import operations

    with PloneClient.from_profile("blog") as site:
        result = operations.create_with_files(
            site,
            "/news",
            "News Item",
            ["lead.jpg", "photo-2.jpg"],
            title="Our new office",
            publish="publish",
        )
        print(result.item["@id"])
"""

from . import blocks
from .exceptions import PloneAPIError
from .exceptions import PloneClientError
from .exceptions import PloneOperationError
from .managers.files import file_data
from collections.abc import Iterable
from collections.abc import Iterator
from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from dataclasses import field
from pathlib import Path
from typing import Any
from typing import Literal
from typing import TYPE_CHECKING

import mimetypes
import re
import unicodedata


if TYPE_CHECKING:
    from .client import PloneClient


#: Keys kept from an item in a result.
ITEM_KEYS = ("@id", "@type", "UID", "id", "title", "review_state")
#: Extensions of the files that :func:`upload_tree` can turn into pages.
PAGE_FORMATS: dict[str, blocks.SourceFormat] = {
    ".md": "markdown",
    ".markdown": "markdown",
    ".html": "html",
    ".htm": "html",
}
#: Files that hold the content of their folder's page in :func:`upload_tree`.
INDEX_NAMES = ("index.md", "README.md", "index.html")

LeadImage = int | Literal["first"] | None


@dataclass
class OperationResult:
    """What an operation did.

    :param operation: Name of the operation.
    :param dry_run: Whether the requests that change the site were skipped.
    :param item: The main item, for operations that create one.
    :param created: Items created, in order; ``source`` names the local file
        or folder they came from, and ``planned`` marks a path guessed in a
        dry run.
    :param changed: Items changed, with what changed.
    :param requests: Every request sent or skipped: ``method``, ``url``,
        ``status`` and, when skipped, ``dry_run``.
    :param error: Type and message of the error that stopped the operation.
    """

    operation: str
    dry_run: bool
    item: dict[str, Any] | None = None
    created: list[dict[str, Any]] = field(default_factory=list)
    changed: list[dict[str, Any]] = field(default_factory=list)
    requests: list[dict[str, Any]] = field(default_factory=list)
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """The result as JSON-ready data.

        :returns: Every field; ``item`` and ``error`` only when set.
        """
        data: dict[str, Any] = {"operation": self.operation, "dry_run": self.dry_run}
        if self.item is not None:
            data["item"] = self.item
        data.update(created=self.created, changed=self.changed, requests=self.requests)
        if self.error is not None:
            data["error"] = self.error
        return data


@contextmanager
def _operation(client: "PloneClient", name: str) -> Iterator[OperationResult]:
    """Run an operation: record its requests and report a failure part way.

    :param client: The client.
    :param name: Name of the operation.
    :returns: The result, filled in by the operation.
    :raises PloneOperationError: If a request fails.
    """
    result = OperationResult(operation=name, dry_run=client.dry_run)
    with client.recording() as requests:
        result.requests = requests
        try:
            yield result
        except PloneClientError as error:
            result.error = {"type": error.__class__.__name__, "message": str(error)}
            if isinstance(error, PloneAPIError):
                result.error = error.to_dict()
            raise PloneOperationError(f"{name} stopped: {error}", result) from error


def _summary(item: Mapping[str, Any], **extra: Any) -> dict[str, Any]:
    """Short form of an item for a result.

    :param item: A serialized item.
    :param extra: Keys to add.
    :returns: The keys in :data:`ITEM_KEYS`, and ``extra``.
    """
    return {**{key: item[key] for key in ITEM_KEYS if key in item}, **extra}


def slug(text: str) -> str:
    """A likely id for a title, close to what Plone generates.

    Only used to name items in a dry run, before Plone picks the real id.

    :param text: The title or file name.
    :returns: Lower case ASCII words joined by ``-``; dots of file names kept.
    """
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w.]+", "-", text.lower()).strip("-.")
    return text or "item"


def _created(
    client: "PloneClient",
    answer: Mapping[str, Any],
    parent: str,
    data: Mapping[str, Any],
    **extra: Any,
) -> dict[str, Any]:
    """Entry for a new item; a planned one in a dry run.

    :param client: The client.
    :param answer: What the site answered, or the dry run log entry.
    :param parent: Site path of the folder.
    :param data: Field values sent, for the planned id.
    :param extra: Keys to add, such as ``source``.
    :returns: The entry; its ``@id`` is the item's URL.
    """
    if not client.dry_run:
        return _summary(answer, **extra)
    item_id = data.get("id") or slug(str(data.get("title") or "item"))
    url = client.site_url(f"{parent.rstrip('/')}/{item_id}")
    return {
        "@id": url,
        "@type": data.get("@type"),
        "id": item_id,
        "title": data.get("title"),
        "planned": True,
        **extra,
    }


def _check_files(paths: Iterable[str | Path]) -> list[Path]:
    """Local files, checked before anything is sent.

    :param paths: Paths of the files.
    :returns: The paths.
    :raises ValueError: If a path is not a file.
    """
    files = [Path(path).expanduser() for path in paths]
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise ValueError(f"Not a file: {', '.join(missing)}")
    return files


def _is_image(path: Path) -> bool:
    """Say whether a file is an image, from its name.

    :param path: The file.
    :returns: ``True`` for ``image/*`` content types.
    """
    return (mimetypes.guess_type(path.name)[0] or "").startswith("image/")


def _pick_lead(files: list[Path], lead_image: LeadImage) -> Path | None:
    """The file to use as lead image.

    :param files: The files.
    :param lead_image: Index in ``files``, ``"first"`` for the first image,
        or ``None``.
    :returns: The file, or ``None``.
    :raises ValueError: If the index is out of range or not an image.
    """
    if lead_image is None:
        return None
    if lead_image == "first":
        return next((path for path in files if _is_image(path)), None)
    try:
        lead = files[lead_image]
    except IndexError:
        raise ValueError(f"lead_image {lead_image} is not one of the files") from None
    if not _is_image(lead):
        raise ValueError(f"{lead.name} is not an image")
    return lead


def _default_blocks(
    schema: Mapping[str, Any], data: Mapping[str, Any]
) -> dict[str, Any]:
    """Title and description blocks, for types with blocks.

    :param schema: ``properties`` of the type's schema.
    :param data: Field values given.
    :returns: ``blocks`` and ``blocks_layout``, or nothing when the type has
        no blocks or blocks are given.
    """
    if "blocks" not in schema or "blocks" in data:
        return {}
    return blocks.build(blocks.title(), blocks.description())


def create_with_files(
    client: "PloneClient",
    parent: str,
    portal_type: str,
    files: Iterable[str | Path],
    *,
    data: Mapping[str, Any] | None = None,
    lead_image: LeadImage = "first",
    publish: str | None = None,
    **fields: Any,
) -> OperationResult:
    """Create an item, upload files and images inside it, and set its lead image.

    The lead image goes where the type keeps it: in the ``image`` field when
    the type has one (the file is then not uploaded again), or otherwise as
    an Image inside the item that ``preview_image_link`` points to, which
    is how News Items work on Volto sites. Files are uploaded as ``Image``
    or ``File`` items, in order. Types with blocks get title and
    description blocks unless blocks are given.

    The item must be folderish to hold the files: on Volto sites, Documents
    and News Items are.

    :param client: The client.
    :param parent: Path or URL of the folder.
    :param portal_type: Content type, such as ``News Item``.
    :param files: Paths of the files to upload inside the item.
    :param data: Field values of the item.
    :param lead_image: Index of the lead image in ``files``, ``"first"``
        for the first image (skipped when the type has no lead image), or
        ``None`` for no lead image.
    :param publish: Workflow transition to run at the end, such as
        ``publish``.
    :param fields: More field values, merged over ``data``.
    :returns: The result; ``item`` is the new item.
    :raises ValueError: If a file is missing, or the lead image is not an
        image or cannot be stored by the type. Nothing is changed then.
    :raises PloneOperationError: If a request fails.
    """
    paths = _check_files(files)
    lead = _pick_lead(paths, lead_image)
    with _operation(client, "create_with_files") as result:
        parent_path = client.content.resolve(parent)
        schema = client.types.get(portal_type).get("properties", {})
        body = {**(data or {}), **fields}
        body.update(_default_blocks(schema, body))
        in_field = lead is not None and "image" in schema
        if lead is not None and not in_field and "preview_image_link" not in schema:
            if lead_image != "first":
                raise ValueError(f"{portal_type} has no lead image field")
            lead = None
        if in_field and lead is not None:
            body["image"] = file_data(lead)
        answer = client.content.create(parent_path, portal_type, body)
        item = _created(client, answer, parent_path, {"@type": portal_type, **body})
        result.item = item
        result.created.append(item)
        item_path = client.path(item["@id"])
        lead_entry: dict[str, Any] | None = None
        for path in paths:
            if in_field and path == lead:
                continue
            uploaded = client.files.upload(item_path, path)
            entry = _created(
                client,
                uploaded,
                item_path,
                {
                    "@type": "Image" if _is_image(path) else "File",
                    "title": path.name,
                },
                source=str(path),
            )
            result.created.append(entry)
            if path == lead:
                lead_entry = entry
        if lead_entry is not None:
            target = lead_entry.get("UID") or lead_entry["@id"]
            client.content.update(
                item_path, preview_image_link=target, representation=False
            )
            result.changed.append({
                "@id": item["@id"],
                "fields": {"preview_image_link": lead_entry["@id"]},
            })
        if publish:
            client.workflow.transition(item_path, publish)
            result.changed.append({"@id": item["@id"], "transition": publish})
        if not client.dry_run:
            result.item = _summary(client.content.get(item_path, include_items=False))
    return result


H1_MARKDOWN_RE = re.compile(r"\A\s*#[ \t]+(?P<title>[^\n]+?)[ \t#]*(?:\n|\Z)")
H1_HTML_RE = re.compile(r"\A\s*<h1[^>]*>(?P<title>.*?)</h1>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")


def split_title(source: str, source_format: blocks.SourceFormat) -> tuple[str, str]:
    """Take a leading level 1 heading out of Markdown or HTML.

    :param source: The Markdown or HTML.
    :param source_format: ``markdown`` or ``html``.
    :returns: The heading text (empty when there is none) and the rest.
    """
    pattern = H1_MARKDOWN_RE if source_format == "markdown" else H1_HTML_RE
    match = pattern.match(source)
    if not match:
        return "", source
    title = " ".join(TAG_RE.sub("", match["title"]).split())
    return title, source[match.end() :].lstrip("\n")


def page_data(
    source: str,
    source_format: blocks.SourceFormat = "markdown",
    *,
    title: str | None = None,
    description: str | None = None,
    default_title: str = "",
) -> dict[str, Any]:
    """Field values of a page made from Markdown or HTML.

    The page gets a title block, a description block and the converted
    content. Without a title, the leading level 1 heading is the title, and
    is not repeated in the content.

    :param source: The Markdown or HTML.
    :param source_format: ``markdown`` or ``html``.
    :param title: Title of the page.
    :param description: Description of the page.
    :param default_title: Title when there is neither ``title`` nor a
        leading heading, such as the name of the file.
    :returns: ``title``, maybe ``description``, ``blocks`` and
        ``blocks_layout``.
    :raises ValueError: If there is no title.
    :raises PloneConfigurationError: If ``collective.html2blocks`` is missing.
    """
    if not title:
        title, source = split_title(source, source_format)
    title = title or default_title
    if not title:
        raise ValueError("A title is needed: pass one, or start with a # heading")
    data: dict[str, Any] = {"title": title}
    if description:
        data["description"] = description
    data.update(
        blocks.convert(
            source,
            source_format,
            before=[blocks.title(), blocks.description()],
        )
    )
    return data


def create_page(
    client: "PloneClient",
    parent: str,
    source: str,
    *,
    source_format: blocks.SourceFormat = "markdown",
    portal_type: str = "Document",
    title: str | None = None,
    description: str | None = None,
    data: Mapping[str, Any] | None = None,
    publish: str | None = None,
) -> OperationResult:
    """Create a page from Markdown or HTML, converted to blocks.

    See :func:`page_data` for how the page is built. Needs the ``markdown``
    extra (Python 3.12 or later).

    :param client: The client.
    :param parent: Path or URL of the folder.
    :param source: The Markdown or HTML text.
    :param source_format: ``markdown`` or ``html``.
    :param portal_type: Content type; it must have blocks.
    :param title: Title; the leading ``#`` heading by default.
    :param description: Description.
    :param data: More field values, such as ``id`` or ``subjects``.
    :param publish: Workflow transition to run at the end.
    :returns: The result; ``item`` is the new page.
    :raises ValueError: If there is no title. Nothing is sent then.
    :raises PloneConfigurationError: If ``collective.html2blocks`` is missing.
    :raises PloneOperationError: If a request fails.
    """
    body = {
        **(data or {}),
        **page_data(source, source_format, title=title, description=description),
    }
    with _operation(client, "create_page") as result:
        parent_path = client.content.resolve(parent)
        answer = client.content.create(parent_path, portal_type, body)
        item = _created(client, answer, parent_path, {"@type": portal_type, **body})
        result.item = item
        result.created.append(item)
        if publish:
            client.workflow.transition(client.path(item["@id"]), publish)
            result.changed.append({"@id": item["@id"], "transition": publish})
            if not client.dry_run:
                result.item = _summary(
                    client.content.get(item["@id"], include_items=False)
                )
    return result


def _folder_body(
    directory: Path, convert_pages: bool, include_hidden: bool
) -> tuple[dict[str, Any], Path | None]:
    """Field values of the page made for a folder.

    :param directory: The folder.
    :param convert_pages: Use its index file, if any, as content.
    :param include_hidden: Whether hidden files are uploaded.
    :returns: The values, and the index file used.
    """
    if convert_pages:
        for name in INDEX_NAMES:
            index = directory / name
            if index.is_file() and (include_hidden or not name.startswith(".")):
                body = page_data(
                    index.read_text(),
                    PAGE_FORMATS[index.suffix.lower()],
                    default_title=directory.name,
                )
                return {"id": slug(directory.name), **body}, index
    return {
        "id": slug(directory.name),
        "title": directory.name,
        **blocks.build(blocks.title(), blocks.description()),
    }, None


def upload_tree(
    client: "PloneClient",
    source: str | Path,
    parent: str,
    *,
    folder_type: str = "Document",
    convert_pages: bool = False,
    include_hidden: bool = False,
    publish: str | None = None,
) -> OperationResult:
    """Upload the contents of a local folder, keeping its structure.

    Folders become folderish pages (``Document`` by default, which is
    folderish on Volto sites), images become ``Image`` items, and other files
    ``File`` items. The contents of ``source`` go inside ``parent``, which
    must exist, as with ``rsync source/ parent``.

    With ``convert_pages``, Markdown and HTML files become pages (see
    :func:`page_data`), and a folder's ``index.md``, ``README.md`` or
    ``index.html`` becomes the content of the folder's own page. This needs
    the ``markdown`` extra.

    :param client: The client.
    :param source: Local folder.
    :param parent: Path or URL of the folder in the site.
    :param folder_type: Content type for folders.
    :param convert_pages: Turn Markdown and HTML files into pages.
    :param include_hidden: Also upload files and folders whose name starts
        with a dot.
    :param publish: Workflow transition to run on each new page, such as
        ``publish``; files and images follow their folder.
    :returns: The result; each created entry names its local ``source``.
    :raises ValueError: If ``source`` is not a folder. Nothing is sent then.
    :raises PloneOperationError: If a request fails.
    """
    root = Path(source).expanduser()
    if not root.is_dir():
        raise ValueError(f"Not a folder: {root}")
    with _operation(client, "upload_tree") as result:
        parent_path = client.content.resolve(parent)
        client.content.get(parent_path, include_items=False)  # it must exist
        _upload_folder(
            client,
            result,
            root,
            parent_path,
            folder_type=folder_type,
            convert_pages=convert_pages,
            include_hidden=include_hidden,
            publish=publish,
            skip=None,
        )
    return result


def _upload_folder(
    client: "PloneClient",
    result: OperationResult,
    directory: Path,
    parent: str,
    *,
    folder_type: str,
    convert_pages: bool,
    include_hidden: bool,
    publish: str | None,
    skip: Path | None,
) -> None:
    """Upload the entries of a local folder into a folder of the site.

    :param client: The client.
    :param result: The result to fill in.
    :param directory: Local folder.
    :param parent: Site path of the folder.
    :param folder_type: Content type for folders.
    :param convert_pages: Turn Markdown and HTML files into pages.
    :param include_hidden: Upload hidden entries.
    :param publish: Transition for new pages.
    :param skip: Index file already used for the folder's page.
    """
    entries = sorted(directory.iterdir(), key=lambda path: path.name.lower())
    for path in entries:
        if path == skip or (path.name.startswith(".") and not include_hidden):
            continue
        if path.is_dir():
            body, index = _folder_body(path, convert_pages, include_hidden)
            answer = client.content.create(parent, folder_type, body)
            entry = _created(
                client, answer, parent, {"@type": folder_type, **body}, source=str(path)
            )
            result.created.append(entry)
            folder = client.path(entry["@id"])
            if publish:
                client.workflow.transition(folder, publish)
            _upload_folder(
                client,
                result,
                path,
                folder,
                folder_type=folder_type,
                convert_pages=convert_pages,
                include_hidden=include_hidden,
                publish=publish,
                skip=index,
            )
        elif convert_pages and path.suffix.lower() in PAGE_FORMATS:
            body = {
                "id": slug(path.stem),
                **page_data(
                    path.read_text(),
                    PAGE_FORMATS[path.suffix.lower()],
                    default_title=path.stem,
                ),
            }
            answer = client.content.create(parent, "Document", body)
            entry = _created(
                client, answer, parent, {"@type": "Document", **body}, source=str(path)
            )
            result.created.append(entry)
            if publish:
                client.workflow.transition(client.path(entry["@id"]), publish)
        elif path.is_file():
            answer = client.files.upload(parent, path)
            data = {"@type": "Image" if _is_image(path) else "File", "title": path.name}
            result.created.append(
                _created(client, answer, parent, data, source=str(path))
            )


def _transfer(
    client: "PloneClient",
    name: str,
    sources: str | Iterable[str],
    target: str,
) -> OperationResult:
    """Copy or move items, and report where each one went.

    :param client: The client.
    :param name: ``copy`` or ``move``.
    :param sources: Items to copy or move.
    :param target: Folder to copy or move into.
    :returns: The result.
    """
    refs = [sources] if isinstance(sources, str) else list(sources)
    with _operation(client, name) as result:
        target_path = client.content.resolve(target)
        folder = client.content.get(target_path, include_items=False)
        if folder.get("is_folderish") is False:
            raise ValueError(f"{target_path} is not a folder")
        paths = [client.content.resolve(ref) for ref in refs]
        counts = {path: client.search.count(path) for path in paths}
        method = client.content.move if name == "move" else client.content.copy
        answer = method(paths, target_path)
        if client.dry_run:
            pairs = [
                (path, f"{target_path.rstrip('/')}/{path.rsplit('/', 1)[-1]}")
                for path in paths
            ]
        else:
            pairs = [
                (client.path(entry["source"]), client.path(entry["target"]))
                for entry in answer
            ]
        for source_path, target_item in pairs:
            entry: dict[str, Any] = {
                "source": client.site_url(source_path),
                "@id": client.site_url(target_item),
                "items": counts.get(source_path),
            }
            if client.dry_run:
                entry["planned"] = True
            else:
                entry["items_after"] = client.search.count(target_item)
            (result.changed if name == "move" else result.created).append(entry)
    return result


def copy_items(
    client: "PloneClient", sources: str | Iterable[str], target: str
) -> OperationResult:
    """Copy items, folders with their contents, into a folder.

    Plone may rename a copy whose id is taken (``copy_of_news``), so read
    the ``@id`` of each created entry.

    :param client: The client.
    :param sources: Path, URL or UID reference of an item, or several.
    :param target: Path or URL of the folder.
    :returns: The result; each created entry has the ``source``, the new
        ``@id``, and the number of ``items`` (the item and everything inside
        it) before and, unless in a dry run, after the copy.
    :raises PloneOperationError: If a request fails.
    """
    return _transfer(client, "copy", sources, target)


def move_items(
    client: "PloneClient", sources: str | Iterable[str], target: str
) -> OperationResult:
    """Move items, folders with their contents, into a folder.

    :param client: The client.
    :param sources: Path, URL or UID reference of an item, or several.
    :param target: Path or URL of the folder.
    :returns: The result; each changed entry has the old ``source``, the
        new ``@id`` and the number of ``items`` before and after the move.
    :raises PloneOperationError: If a request fails.
    """
    return _transfer(client, "move", sources, target)
