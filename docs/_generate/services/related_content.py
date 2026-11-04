# Examples are shown as written, so they may be long.
"""Examples of comments, aliases, relations and translations."""

from service_example import Example


NOT_RUN: dict[str, str] = {}

COMMENTS = (
    'client.addons.install("plone.app.discussion")\n'
    'client.registry.set("plone.app.discussion.interfaces.IDiscussionSettings.globally_enabled", True)\n'
    'client.registry.set("plone.app.discussion.interfaces.IDiscussionSettings.edit_comment_enabled", True)\n'
    'client.content.update("/news/release-6-2", allow_discussion=True)'
)
FIRST = 'comment_id = next(client.comments.list("/news/release-6-2"))["comment_id"]\n'
LANGUAGES = (
    'client.registry.update({"plone.available_languages": ["en", "pt-br"]})\n'
    'client.addons.install("plone.app.multilingual")\n'
    'client.content.create("/en", "Document", id="about-us", title="About us")\n'
    'client.content.create("/pt-br", "Document", id="sobre", title="Sobre")'
)

EXAMPLES = [
    Example(
        "comments.create",
        'client.comments.create("/news/release-6-2", "Great news!")',
        setup=COMMENTS,
        doc="comments",
    ),
    Example(
        "comments.list",
        'list(client.comments.list("/news/release-6-2"))',
        keep=("author_username", "text"),
        doc="comments",
    ),
    Example(
        "comments.update",
        FIRST
        + 'client.comments.update("/news/release-6-2", comment_id, "Great news, everyone!")',
        doc="comments",
    ),
    Example(
        "comments.delete",
        FIRST + 'client.comments.delete("/news/release-6-2", comment_id)',
        doc="comments",
    ),
    Example(
        "aliases.create",
        'client.aliases.create("/news/release-6-2", "/news/plone-6-2")',
        cli="plone-client aliases add /news/release-6-2 /news/plone-62 -f items_total",
        # Plone 6.2 adds datetime, manual and redirect-to to each alias.
        keep=("items", "items_total"),
        item_keep=("path",),
        doc="aliases",
    ),
    Example(
        "aliases.list",
        'client.aliases.list("/news/release-6-2")',
        cli="plone-client aliases list /news/release-6-2 -f items_total",
        keep=("items", "items_total"),
        item_keep=("path",),
        doc="aliases",
    ),
    Example(
        "aliases.delete",
        'client.aliases.delete("/news/release-6-2", "/news/plone-6-2")',
        cli="plone-client aliases remove /news/release-6-2 /news/plone-62",
        doc="aliases",
    ),
    Example(
        "aliases.create_redirects",
        'client.aliases.create_redirects(\n    [{"path": "/old-news", "redirect-to": "/news"}]\n)',
        undo='client.aliases.delete("/", "/old-news")',
        doc="aliases",
    ),
    Example(
        "relations.create",
        "client.relations.create(\n    [\n        {\n"
        '            "source": "/news/release-6-2",\n'
        '            "target": "/about",\n'
        '            "relation": "relatedItems",\n        }\n    ]\n)',
        doc="relations",
    ),
    Example(
        "relations.stats",
        "client.relations.stats()",
        keep=("stats", "broken"),
        doc="relations",
    ),
    Example(
        "relations.list",
        'client.relations.list(relation="relatedItems")["relations"]["relatedItems"]',
        keep=("items_total",),
        doc="relations",
    ),
    Example(
        "relations.delete",
        'client.relations.delete(relation="relatedItems")',
        doc="relations",
    ),
    Example(
        "relations.rebuild",
        "client.relations.rebuild()",
        doc="relations",
    ),
    Example(
        "translations.link",
        'client.translations.link("/en/about-us", "/pt-br/sobre")',
        setup=LANGUAGES,
        doc="translations",
    ),
    Example(
        "translations.get",
        'client.translations.get("/en/about-us")',
        keep=("@id", "items"),
        item_keep=("@id", "language"),
        doc="translations",
    ),
    Example(
        "translations.locate",
        'client.translations.locate("/en/about-us", "pt-br")',
        doc="translations",
    ),
    Example(
        "translations.unlink",
        'client.translations.unlink("/en/about-us", "pt-br")',
        doc="translations",
    ),
]
