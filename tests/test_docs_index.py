"""The landing page of the documentation links every path and every section."""

from pathlib import Path

import pytest
import re


INDEX = Path(__file__).parents[1] / "docs" / "index.md"
LINK = re.compile(r"^:link:\s*(\S+)\s*$", re.MULTILINE)


@pytest.fixture(scope="module")
def links() -> set[str]:
    return set(LINK.findall(INDEX.read_text(encoding="utf-8")))


@pytest.mark.parametrize(
    "target",
    [
        "start/script",
        "start/cli",
        "start/agents",
        "tutorials/index",
        "how-to/index",
        "reference/index",
        "explanation/index",
    ],
)
def test_index_links(links, target):
    assert target in links
    assert (INDEX.parent / f"{target}.md").is_file()
