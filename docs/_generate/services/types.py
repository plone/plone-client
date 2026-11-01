# Examples are shown as written, so they may be long.
"""Examples of ``client.types``, ``client.block_types`` and ``client.vocabularies``."""

from service_example import Example


NOT_RUN = {
    "vocabularies.source": "no field of the default content types has an iterable source.",
    "vocabularies.querysource": "no field of the default content types has a query source.",
}

EXAMPLES = [
    Example(
        "types.list",
        'client.types.list("/news")',
        cli="plone-client types --addable-in /news -c",
        keep=("@id", "title", "addable"),
        limit=3,
        doc="types",
    ),
    Example(
        "types.addable",
        'client.types.addable("/news")',
        doc="types",
    ),
    Example(
        "types.get",
        'client.types.get("News Item")',
        cli='plone-client types "News Item" -f title,required',
        keep=("title", "required"),
        doc="types",
    ),
    Example(
        "types.create_field",
        'client.types.create_field(\n    "sample",\n'
        '    {"factory": "Text line (String)", "title": "Short name", "required": False},\n)',
        setup='client.controlpanels.create("dexterity-types", {"title": "Sample"})',
        keep=("title", "factory"),
        doc="types",
    ),
    Example(
        "types.get_field",
        'client.types.get_field("sample", "short_name")',
        keep=("title", "type", "factory"),
        doc="types",
    ),
    Example(
        "types.update",
        'client.types.update("sample", {"title": "Nickname"}, name="short_name")',
        doc="types",
    ),
    Example(
        "types.replace",
        'schema = client.types.get("sample")\nclient.types.replace("sample", schema)',
        doc="types",
    ),
    Example(
        "types.delete_field",
        'client.types.delete_field("sample", "short_name")',
        undo='client.controlpanels.delete("dexterity-types", "sample")',
        doc="types",
    ),
    Example(
        "block_types.list",
        "client.block_types.list()",
        cli="plone-client block-types -f source",
        keep=("source", "items", "items_total"),
        item_keep=("id", "title"),
        limit=3,
    ),
    Example(
        "block_types.get",
        'client.block_types.get("teaser")',
        cli="plone-client block-types teaser -f id,title",
        keep=("id", "title", "source"),
    ),
    Example(
        "block_types.markdown",
        'client.block_types.markdown("title").splitlines()[0]',
        cli="plone-client block-types title --markdown | head -1",
    ),
    Example(
        "vocabularies.list",
        "client.vocabularies.list()",
        keep=("@id", "title"),
        limit=2,
        doc="vocabularies",
    ),
    Example(
        "vocabularies.get",
        'client.vocabularies.get("plone.app.vocabularies.ReallyUserFriendlyTypes", title="news")',
        cli="plone-client vocabulary plone.app.vocabularies.ReallyUserFriendlyTypes --title news",
        keep=("items", "items_total"),
        doc="vocabularies",
    ),
    Example(
        "vocabularies.iter",
        'list(client.vocabularies.iter("plone.app.vocabularies.WorkflowStates"))',
        limit=3,
        doc="vocabularies",
    ),
    Example(
        "vocabularies.source",
        'client.vocabularies.source("/about", "my_field")',
        doc="vocabularies",
    ),
    Example(
        "vocabularies.querysource",
        'client.vocabularies.querysource("/about", "my_field", "plone")',
        doc="vocabularies",
    ),
]
