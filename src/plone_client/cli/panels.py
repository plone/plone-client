"""Help panels that group the commands in ``--help``.

The root panels group commands by what they act on; the panels of each
command group separate reading from changing.
"""

# Root panels, in the order they are shown.
CONTENT_READ = "Content — read"
CONTENT_CHANGE = "Content — change"
CONTENT_FILES = "Content — files"
SITE = "Site — users, settings & types"
ADVANCED = "Advanced"
CONFIGURATION = "Configuration — connection, profiles & agents"

# Panels inside a command group.
BROWSE = "Browse"
WRITE = "Write"
MEMBERSHIP = "Membership"
CONNECTION = "Connection"

#: Root commands, in the order ``plone-client --help`` lists them.
ROOT_ORDER: tuple[str, ...] = (
    # Content — read
    "get",
    "ls",
    "search",
    "resolve",
    "blocks",
    "history",
    "sharing",
    # Content — change
    "create",
    "update",
    "workflow",
    "copy",
    "move",
    "order",
    "delete",
    # Content — files
    "upload",
    "download",
    # Site
    "types",
    "vocabulary",
    "users",
    "groups",
    "registry",
    "aliases",
    # Advanced
    "request",
    # Configuration
    "info",
    "profile",
    "skill",
)
