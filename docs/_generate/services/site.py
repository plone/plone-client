# Examples are shown as written, so they may be long.
"""Examples of the site settings managers."""

from service_example import Example


TITLE = "plone.site_title"
ORIGINAL = "Welcome to Plone 6"
RULE = {
    "title": "Log new comments",
    "description": "A sample rule.",
    "event": "Comment added",
    "enabled": True,
    "cascading": False,
    "stop": False,
}

NOT_RUN = {
    "system.email_send": "the site needs a mail server.",
    "system.email_notification": "the site needs a mail server.",
}

EXAMPLES = [
    Example(
        "registry.get",
        f'client.registry.get("{TITLE}")',
        cli=f"plone-client registry get {TITLE}",
        doc="registry",
    ),
    Example(
        "registry.list",
        'list(client.registry.list("plone.site_"))',
        cli="plone-client registry list plone.site_ --limit 1 -f name,value",
        keep=("name", "value"),
        limit=2,
        doc="registry",
    ),
    Example(
        "registry.update",
        f'client.registry.update({{"{TITLE}": "Sample site"}})',
        doc="registry",
    ),
    Example(
        "registry.set",
        f'client.registry.set("{TITLE}", "Plone site")',
        cli=f"plone-client registry set {TITLE} '\"Plone site\"'",
        undo=f'client.registry.set("{TITLE}", "{ORIGINAL}")',
        doc="registry",
    ),
    Example(
        "controlpanels.list",
        "client.controlpanels.list()",
        keep=("@id", "title", "group"),
        limit=2,
        doc="controlpanels",
    ),
    Example(
        "controlpanels.get",
        'client.controlpanels.get("editing")',
        keep=("@id", "title", "group"),
        doc="controlpanels",
    ),
    Example(
        "controlpanels.update",
        'client.controlpanels.update("editing", {"ext_editor": False})',
        doc="controlpanels",
    ),
    Example(
        "controlpanels.create",
        'client.controlpanels.create("dexterity-types", {"title": "Event page"})',
        keep=("@id", "title"),
        doc="controlpanels",
    ),
    Example(
        "controlpanels.delete",
        'client.controlpanels.delete("dexterity-types", "event_page")',
        doc="controlpanels",
    ),
    Example(
        "addons.list",
        "client.addons.list()",
        keep=("items",),
        item_keep=("id", "title", "is_installed"),
        limit=2,
        doc="addons",
    ),
    Example(
        "addons.get",
        'client.addons.get("plone.session")',
        keep=("id", "title", "is_installed", "profile_type"),
        doc="addons",
    ),
    Example(
        "addons.install",
        'client.addons.install("plone.session")',
        doc="addons",
    ),
    Example(
        "addons.upgrade",
        'client.addons.upgrade("plone.session")',
        doc="addons",
    ),
    Example(
        "addons.install_profile",
        'client.addons.install_profile("plone.session", "default")',
        doc="addons",
    ),
    Example(
        "addons.uninstall",
        'client.addons.uninstall("plone.session")',
        doc="addons",
    ),
    Example(
        "content_rules.assign",
        'client.content_rules.assign("/news", "rule-1")',
        setup=f'client.controlpanels.create("content-rules", {RULE!r})',
        doc="content-rules",
    ),
    Example(
        "content_rules.get",
        'client.content_rules.get("/news")["content-rules"]',
        keep=("assigned_rules",),
        item_keep=("id", "title", "enabled", "bubbles"),
        doc="content-rules",
    ),
    Example(
        "content_rules.apply_to_subfolders",
        'client.content_rules.apply_to_subfolders("/news", "rule-1")',
        doc="content-rules",
    ),
    Example(
        "content_rules.disable",
        'client.content_rules.disable("/news", "rule-1")',
        doc="content-rules",
    ),
    Example(
        "content_rules.enable",
        'client.content_rules.enable("/news", "rule-1")',
        doc="content-rules",
    ),
    Example(
        "content_rules.move",
        'client.content_rules.move("/news", "rule-1", up=False)',
        doc="content-rules",
    ),
    Example(
        "content_rules.unassign",
        'client.content_rules.unassign("/news", "rule-1")',
        undo='client.controlpanels.delete("content-rules", "rule-1")',
        doc="content-rules",
    ),
    Example(
        "system.site",
        "client.system.site()",
        keep=("plone.site_title", "plone.available_languages", "features"),
        doc="site",
    ),
    Example(
        "system.system",
        "client.system.system()",
        keep=("plone_version", "plone_restapi_version", "python_version"),
        doc="system",
    ),
    Example(
        "system.database",
        "client.system.database()",
        keep=("@id", "db_name"),
        doc="database",
    ),
    Example(
        "system.transactions",
        "client.system.transactions()",
        keep=("description", "username"),
        limit=1,
        doc="transactions",
    ),
    Example(
        "system.revert_transactions",
        "latest = client.system.transactions()[0]\n"
        'client.system.revert_transactions(latest["id"])',
        setup=f'client.registry.set("{TITLE}", "Undo me")',
        undo=f'client.registry.set("{TITLE}", "{ORIGINAL}")',
        doc="transactions",
    ),
    Example(
        "system.upgrade_info",
        "client.system.upgrade_info()",
        keep=("@id", "upgrade_steps"),
        doc="upgrade",
    ),
    Example(
        "system.upgrade",
        "client.system.upgrade(dry_run=True)",
        keep=("@id", "dry_run", "upgraded"),
        doc="upgrade",
    ),
    Example(
        "system.login_providers",
        "client.system.login_providers()",
        doc="login",
    ),
    Example(
        "system.email_send",
        'client.system.email_send(\n    "editor@example.org",\n    "site@example.org",\n'
        '    "The report is ready.",\n    subject="Report",\n)',
        doc="email-send",
    ),
    Example(
        "system.email_notification",
        'client.system.email_notification(\n    "reader@example.org",\n'
        '    "I have a question.",\n    subject="Question",\n)',
        doc="email-notification",
    ),
]
