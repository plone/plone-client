"""Sphinx configuration for the plone-client documentation.

The API reference uses ``sphinx.ext.autodoc``: the package imports cleanly
without Plone, and its docstrings are reStructuredText field lists.
"""

from datetime import datetime
from packaging.version import Version
from pathlib import Path

import sys


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from plone_client import __version__  # noqa: E402


project = "plone-client"
author = "Plone Community"
trademark_name = "Plone"
copyright = str(datetime.now().year)  # noqa: A001
# The full version, including alpha/beta/rc tags.
release = __version__
# The short X.Y version.
version = "v" + Version(release).base_version

templates_path = ["_templates"]

extensions = [
    "myst_parser",
    "notfound.extension",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_sitemap",
    "sphinxext.opengraph",
]

exclude_patterns = ["_build", "_examples", "_styles"]

# -- MyST -------------------------------------------------------------------

myst_enable_extensions = [
    "attrs_inline",
    "colon_fence",
    "deflist",
    "linkify",
    "substitution",
]
myst_heading_anchors = 3

# -- autodoc ----------------------------------------------------------------

autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
}
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_mock_imports = ["keyring", "tomlkit", "typer"]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "plone": ("https://6.docs.plone.org/", None),
}

# Report every reference that does not resolve; httpx and keyring publish
# no Sphinx inventory to link to.
nitpicky = True
nitpick_ignore_regex = [
    ("py:class", r"httpx\..*"),
    ("py:mod", r"httpx|keyring"),
]

# -- Link checking ----------------------------------------------------------

linkcheck_ignore = [
    r"http://localhost.*",
    r"http://127\.0\.0\.1.*",
    # Anchors on GitHub are generated client-side.
    r"https://github\.com/.*#.*",
    # The repository is not published yet.
    r"https://github\.com/plone/plone-client.*",
    r"https://plone\.github\.io/plone-client.*",
    r"https://pypi\.org/project/plone-client.*",
]

# -- HTML output ------------------------------------------------------------

html_theme = "plone_sphinx_theme"
html_logo = "_static/logo.svg"
html_favicon = "_static/favicon.ico"

html_theme_options = {
    "icon_links": [
        {
            "name": "GitHub",
            "url": "https://github.com/plone/plone-client",
            "icon": "fa-brands fa-square-github",
            "type": "fontawesome",
        },
        {
            "name": "PyPI",
            "url": "https://pypi.org/project/plone-client/",
            "icon": "fa-brands fa-python",
            "type": "fontawesome",
        },
    ],
    "logo": {"text": "plone-client"},
    "navigation_with_keys": True,
    "path_to_docs": "docs",
    "repository_branch": "main",
    "repository_url": "https://github.com/plone/plone-client",
    "search_bar_text": "Search",
    "show_toc_level": 2,
    "use_edit_page_button": True,
    "use_issues_button": True,
    "use_repository_button": True,
}

html_sidebars = {
    "**": [
        "navbar-logo",
        "search-button-field",
        "sbt-sidebar-nav",
    ]
}

html_title = f"{project} {release}"
html_extra_path = ["robots.txt"]
html_static_path = ["_static"]

html_baseurl = "https://plone.github.io/plone-client"
sitemap_url_scheme = "{link}"
sitemap_filename = "sitemap-custom.xml"

ogp_site_url = html_baseurl
ogp_site_name = project
