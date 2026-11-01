"""Write a generated page, or say that the one in the tree is out of date."""

from pathlib import Path

import sys


GENERATED = Path(__file__).parents[1] / "_generated"


def cell(text: object) -> str:
    """Make a value safe for a Markdown table.

    :param text: The value.
    :returns: Its text on one line, with pipes escaped.
    """
    return " ".join(str(text).split()).replace("|", "\\|")


def publish(name: str, text: str) -> int:
    """Write a file of ``_generated``, or compare it with ``--check``.

    :param name: File name.
    :param text: Its new content.
    :returns: The exit code.
    """
    path = GENERATED / name
    if "--check" in sys.argv:
        if not path.exists() or path.read_text() != text:
            print(f"{path.name} is out of date: run make docs-generate")
            return 1
        print(f"{path.name} is up to date")
        return 0
    GENERATED.mkdir(exist_ok=True)
    path.write_text(text)
    print(f"wrote {path.name}")
    return 0
