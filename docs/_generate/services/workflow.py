"""Examples of ``client.workflow``, ``client.history`` and ``client.working_copy``."""

from service_example import Example


NOT_RUN: dict[str, str] = {}

EXAMPLES = [
    Example(
        "workflow.get",
        'client.workflow.get("/news/release-party")',
        cli="plone-client workflow /news/release-party -f state,transitions",
        keep=("state", "transitions"),
        item_keep=("@id", "title"),
        doc="workflow",
    ),
    Example(
        "workflow.transition",
        'client.workflow.transition(\n    "/news/release-party",\n'
        '    "publish",\n    comment="Ready for readers.",\n)',
        cli="plone-client workflow /news/release-party publish",
        undo='client.workflow.transition("/news/release-party", "retract")',
        keep=("action", "comments", "review_state", "title"),
        doc="workflow",
    ),
    Example(
        "history.list",
        'client.history.list("/about")',
        cli="plone-client history /about -f action,type",
        keep=("action", "type", "transition_title"),
        limit=3,
        doc="history",
    ),
    Example(
        "history.get",
        'client.history.get("/news/old-announcement", 0)',
        setup='client.content.update("/news/old-announcement", title="Older title")\n'
        'client.content.update("/news/old-announcement", title="Old announcement")',
        keep=("@id", "title", "version"),
        doc="history",
    ),
    Example(
        "history.revert",
        'client.history.revert("/news/old-announcement", 0)',
        doc="history",
    ),
    Example(
        "working_copy.create",
        'client.working_copy.create("/about")',
        setup='client.addons.install("plone.app.iterate")',
        doc="workingcopy",
    ),
    Example(
        "working_copy.get",
        'client.working_copy.get("/about")',
        keep=("working_copy",),
        doc="workingcopy",
    ),
    Example(
        "working_copy.check_in",
        'client.working_copy.check_in("/about")',
        doc="workingcopy",
    ),
    Example(
        "working_copy.delete",
        'client.working_copy.delete("/about")',
        setup='client.working_copy.create("/about")',
        undo='client.addons.uninstall("plone.app.iterate")',
        doc="workingcopy",
    ),
]
