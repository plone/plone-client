"""Sphinx configuration for plone-client documentation."""

from pathlib import Path

import sys


sys.path.insert(0, str(Path("..") / "src"))

project = "plone-client"
author = "Your Name"
release = "0.1.0"
copyright = f"2026, {author}"  # noqa: A001

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",  # Google/NumPy docstrings
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx_autodoc_typehints",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "requests": ("https://docs.python-requests.org/en/latest/", None),
}

autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}
autodoc_typehints = "description"
napoleon_google_docstring = False
napoleon_numpy_docstring = True

html_theme = "furo"
html_title = "plone-client"
templates_path: list[str] = []
exclude_patterns = ["_build"]
