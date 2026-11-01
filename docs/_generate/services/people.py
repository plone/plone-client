# Examples are shown as written, so they may be long.
"""Examples of ``client.users``, ``client.groups`` and ``client.sharing``."""

from service_example import Example


NOT_RUN = {
    "users.reset_password": "the site needs a mail server to send the message.",
}

USER = ("id", "fullname", "email", "roles")
GROUP = ("id", "title", "roles")

EXAMPLES = [
    Example(
        "users.list",
        'client.users.list(search="jo")',
        cli="plone-client users list -q jo -f id,fullname",
        keep=("id", "fullname"),
        doc="users",
    ),
    Example(
        "users.get",
        'client.users.get("jdoe")',
        cli="plone-client users get jdoe -f id,email",
        keep=USER,
        doc="users",
    ),
    Example(
        "users.create",
        'client.users.create(\n    "asmith",\n    email="asmith@example.org",\n'
        '    fullname="Ann Smith",\n    password="correct-horse-battery",\n)',
        cli='echo correct-horse-battery | plone-client users create asmith --email asmith@example.org --fullname "Ann Smith" --password-stdin -f id,fullname',
        undo='client.users.delete("asmith")',
        keep=USER,
        doc="users",
    ),
    Example(
        "users.update",
        'client.users.update("jdoe", fullname="Joanna Doe")',
        cli='plone-client users update jdoe -s fullname="Joanna Doe"',
        undo='client.users.update("jdoe", fullname="Jo Doe")',
        doc="users",
    ),
    Example(
        "users.update_password",
        'jdoe_client.users.update_password(\n    "jdoe",\n    "another-long-password",\n'
        '    old_password="correct-horse-battery",\n)',
        setup="from plone_client import PloneClient\n"
        'jdoe_client = PloneClient(client.url, username="jdoe", password="correct-horse-battery")\n'
        "record(jdoe_client)",
        text="`jdoe_client` is a client logged in as `jdoe`: the site refuses this request from anyone else, a Manager included, and without `old_password`.",
        doc="users",
    ),
    Example(
        "users.reset_password",
        'client.users.reset_password("jdoe")',
        doc="users",
    ),
    Example(
        "users.delete",
        'client.users.delete("todelete")',
        setup='client.users.create("todelete", email="d@example.org", password="correct-horse-battery")',
        cli="plone-client users delete todelete --yes",
        undo='client.users.create("todelete", email="d@example.org", password="correct-horse-battery")',
        doc="users",
    ),
    Example(
        "users.schema",
        "client.users.schema()",
        keep=("required", "type"),
        doc="userschema",
    ),
    Example(
        "users.portrait",
        'client.users.portrait("jdoe")',
        setup='client.users.update("jdoe", portrait={"data": "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7", "encoding": "base64", "content-type": "image/gif", "filename": "p.gif"})',
        doc="portrait",
    ),
    Example(
        "groups.list",
        'client.groups.list(query="edit")',
        cli="plone-client groups list -q edit -f id,title",
        keep=GROUP,
        doc="groups",
    ),
    Example(
        "groups.get",
        'client.groups.get("editors")',
        cli="plone-client groups get editors -f id,title",
        keep=(*GROUP, "members"),
        doc="groups",
    ),
    Example(
        "groups.create",
        'client.groups.create("reviewers-team", title="Review team", roles=["Reviewer"])',
        cli='plone-client groups create reviewers-team --title "Review team" --role Reviewer -f id',
        undo='client.groups.delete("reviewers-team")',
        keep=GROUP,
        doc="groups",
    ),
    Example(
        "groups.update",
        'client.groups.update("editors", description="They edit the news.")',
        doc="groups",
    ),
    Example(
        "groups.add_members",
        'client.groups.add_members("editors", "admin")',
        cli="plone-client groups add-member editors admin",
        undo='client.groups.remove_members("editors", "admin")',
        doc="groups",
    ),
    Example(
        "groups.remove_members",
        'client.groups.remove_members("editors", "admin")',
        setup='client.groups.add_members("editors", "admin")',
        cli="plone-client groups remove-member editors admin",
        undo='client.groups.add_members("editors", "admin")',
        doc="groups",
    ),
    Example(
        "groups.delete",
        'client.groups.delete("old-team")',
        setup='client.groups.remove_members("editors", "admin")\n'
        'client.groups.create("old-team", title="Old")',
        cli="plone-client groups delete old-team --yes",
        undo='client.groups.create("old-team", title="Old")',
        doc="groups",
    ),
    Example(
        "sharing.get",
        'client.sharing.get("/about", search="jdoe")',
        setup='client.groups.delete("old-team")',
        cli="plone-client sharing /about --search jdoe -f inherit",
        keep=("inherit", "entries"),
        item_keep=("id", "title", "type"),
        doc="sharing",
    ),
    Example(
        "sharing.update",
        'client.sharing.update(\n    "/about",\n'
        '    [{"id": "jdoe", "type": "user", "roles": {"Reader": True}}],\n)',
        doc="sharing",
    ),
    Example(
        "sharing.principals",
        'client.sharing.principals("jdoe")',
        keep=("users",),
        item_keep=("id", "fullname"),
        doc="principals",
    ),
    Example(
        "sharing.roles",
        "client.sharing.roles()",
        keep=("id", "title"),
        limit=3,
        doc="roles",
    ),
]
