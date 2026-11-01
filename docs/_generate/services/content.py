# Examples are shown as written, so they may be long.
"""Examples of ``client.content``."""

from service_example import Example


NOT_RUN: dict[str, str] = {}

ITEM = ("@id", "@type", "title", "review_state")

EXAMPLES = [
    Example(
        "content.get",
        'client.content.get("/news/release-6-2")',
        cli="plone-client get /news/release-6-2 -f @id,@type,title,review_state",
        keep=ITEM,
        doc="content-types",
    ),
    Example(
        "content.get",
        'client.content.get("/news/release-6-2", expand="breadcrumbs")["@components"]',
        title="Expand a component",
        text="`expand` puts the answer of another service inside the item.",
        cli="plone-client get /news/release-6-2 --expand breadcrumbs -f title",
        keep=("breadcrumbs",),
        doc="content-types",
    ),
    Example(
        "content.find_by_uid",
        'uid = client.content.get("/about")["UID"]\nclient.content.find_by_uid(uid)',
        keep=("@id", "@type", "title"),
        doc="searching",
    ),
    Example(
        "content.resolve",
        'uid = client.content.get("/about")["UID"]\n'
        'client.content.resolve(f"uid:{uid}")',
        doc="searching",
    ),
    Example(
        "content.exists",
        'client.content.exists("/news/no-such-item")',
    ),
    Example(
        "content.children",
        'list(client.content.children("/news", portal_type="News Item"))',
        cli='plone-client ls /news -t "News Item" --limit 2 -f @id,title',
        keep=("@id", "title", "review_state"),
        limit=3,
        doc="searching",
    ),
    Example(
        "content.create",
        'client.content.create(\n    "/news",\n    "News Item",\n'
        '    title="Sprint in Bonn",\n    description="A week of work.",\n)',
        cli='plone-client create /news "News Item" --title "Sprint in Bonn"'
        " -f @id,title,review_state",
        undo='client.content.delete("/news/sprint-in-bonn")',
        keep=("@id", "@type", "id", "title", "review_state"),
        doc="content-types",
    ),
    Example(
        "content.update",
        'client.content.update("/about/team", title="The team")',
        cli='plone-client update /about/team --title "The team" -f title',
        undo='client.content.update("/about/team", title="Team")',
        keep=("@id", "title"),
        doc="content-types",
    ),
    Example(
        "content.delete",
        'client.content.delete("/news/to-remove")',
        setup='client.content.create("/news", "Document", id="to-remove", title="Remove")',
        cli="plone-client delete /news/to-remove --yes",
        undo='client.content.create("/news", "Document", id="to-remove", title="Remove")',
        doc="content-types",
    ),
    Example(
        "content.copy",
        'client.content.copy("/about/team", "/news")',
        cli="plone-client copy /about/team --to /news",
        undo='client.content.delete("/news/team")',
        doc="copymove",
    ),
    Example(
        "content.move",
        'client.content.move("/about/team", "/news")',
        cli="plone-client move /about/team --to /news",
        undo='client.content.move("/news/team", "/about")',
        doc="copymove",
    ),
    Example(
        "content.order",
        'client.content.order("/news", "sprint-report", "top")',
        cli="plone-client order /news sprint-report top",
        undo='client.content.order("/news", "sprint-report", 3)',
        doc="content-types",
    ),
    Example(
        "content.sort",
        'client.content.sort("/news", "sortable_title", "ascending")',
        doc="content-types",
    ),
    Example(
        "content.lock",
        'client.content.lock("/about", timeout=600)',
        undo='client.content.unlock("/about")',
        keep=("locked", "stealable", "timeout", "creator"),
        doc="locking",
    ),
    Example(
        "content.lock_info",
        'client.content.lock_info("/about")',
        keep=("locked", "stealable"),
        doc="locking",
    ),
    Example(
        "content.refresh_lock",
        'client.content.refresh_lock("/about")',
        setup='client.content.lock("/about")',
        keep=("locked", "stealable", "timeout"),
        doc="locking",
    ),
    Example(
        "content.unlock",
        'client.content.unlock("/about")',
        keep=("locked", "stealable"),
        doc="locking",
    ),
    Example(
        "content.link_integrity",
        'uid = client.content.get("/about")["UID"]\nclient.content.link_integrity(uid)',
        keep=("@id", "title", "breaches", "items_total"),
        doc="linkintegrity",
    ),
]
