# Examples are shown as written, so they may be long.
"""Examples of ``client.search`` and ``client.querystring``."""

from service_example import Example


NOT_RUN: dict[str, str] = {}

EXAMPLES = [
    Example(
        "search.search",
        'client.search.search("/news", portal_type="News Item", b_size=2)',
        cli='plone-client search /news -t "News Item" --limit 2 -f @id,title',
        keep=("items", "items_total"),
        item_keep=("@id", "title", "review_state"),
        doc="searching",
    ),
    Example(
        "search.search",
        'client.search.search(\n    query={"created": {"query": "2000-01-01", "range": "min"}},\n'
        '    portal_type="Document",\n    sort_on="sortable_title",\n'
        '    metadata_fields="UID",\n)',
        title="Sort, and ask for more metadata",
        text="`query` takes options of a catalog index, and `metadata_fields` adds columns to each result.",
        keep=("items", "items_total"),
        item_keep=("title", "UID"),
        limit=2,
        doc="searching",
    ),
    Example(
        "search.iter",
        'list(client.search.iter(portal_type="News Item", review_state="private"))',
        cli='plone-client search -t "News Item" --state private -f @id',
        keep=("@id", "title"),
        doc="searching",
    ),
    Example(
        "search.count",
        'client.search.count("/news", review_state="published")',
        cli="plone-client search /news --state published --count",
        doc="searching",
    ),
    Example(
        "querystring.config",
        'sorted(client.querystring.config()["sortable_indexes"])[:3]',
        doc="querystring",
    ),
    Example(
        "querystring.search",
        "client.querystring.search(\n    [\n        {\n"
        '            "i": "portal_type",\n'
        '            "o": "plone.app.querystring.operation.selection.any",\n'
        '            "v": ["News Item"],\n        }\n    ],\n'
        '    sort_on="sortable_title",\n    b_size=2,\n)',
        keep=("items", "items_total"),
        item_keep=("@id", "title"),
        doc="querystringsearch",
    ),
]
