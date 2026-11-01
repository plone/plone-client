"""Examples of ``client.navigation``."""

from service_example import Example


NOT_RUN: dict[str, str] = {}

EXAMPLES = [
    Example(
        "navigation.navigation",
        "client.navigation.navigation(depth=2)",
        keep=("@id", "items"),
        item_keep=("@id", "title"),
        doc="navigation",
    ),
    Example(
        "navigation.breadcrumbs",
        'client.navigation.breadcrumbs("/news/release-6-2")',
        keep=("@id", "items"),
        doc="breadcrumbs",
    ),
    Example(
        "navigation.contextnavigation",
        'client.navigation.contextnavigation("/about")',
        keep=("available", "title", "items"),
        item_keep=("@id", "title"),
        doc="contextnavigation",
    ),
    Example(
        "navigation.navroot",
        'client.navigation.navroot("/news")["navroot"]',
        keep=("@id", "title"),
        doc="navroot",
    ),
    Example(
        "navigation.actions",
        'client.navigation.actions("/news", categories=["user"])',
        keep=("user",),
        item_keep=("id", "title"),
        doc="actions",
    ),
    Example(
        "navigation.inherit",
        'client.navigation.inherit("/news", "plone.allowdiscussion")',
        keep=("@id", "plone.allowdiscussion"),
        doc="inherit",
    ),
]
