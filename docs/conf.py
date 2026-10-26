"""Sphinx configuration for the plone-client documentation."""

from pathlib import Path

import sys


sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from plone_client import __version__  # noqa: E402


project = "plone-client"
author = "Érico Andrei"
release = __version__
copyright = f"2026, {author}"  # noqa: A001

extensions = [
    "myst_parser",
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
]

myst_enable_extensions = ["colon_fence", "deflist"]
myst_heading_anchors = 3

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
}

autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
}
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_mock_imports = ["keyring", "tomlkit", "typer"]

# Report every reference that does not resolve; httpx and keyring publish
# no Sphinx inventory to link to.
nitpicky = True
nitpick_ignore_regex = [
    ("py:class", r"httpx\..*"),
    ("py:mod", r"httpx|keyring"),
]

html_theme = "furo"
html_title = "plone-client"
exclude_patterns = ["_build"]
