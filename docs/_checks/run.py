"""Run the documentation pages against a fresh Plone site, and compare the output.

A page opts in with a ``<!-- check: start -->`` comment; the blocks after it run
in order, in one temporary directory, until ``<!-- check: stop -->``.

* A ``shell`` block runs in ``bash``; a ``python`` block runs in Python.
* A ``json``, ``text`` or ``console`` block right after one of those is the
  output it must print. UIDs, dates, tokens and versions are normalized first.

A comment right before a block changes what happens to it:

* ``<!-- check: skip -->`` ignores the block, and an output block after it.
* ``<!-- check: file NAME -->`` saves the block as a file, whatever its language.
* ``<!-- check: append NAME -->`` adds the block to that file.
* ``<!-- check: exit N -->`` expects exit code ``N`` rather than 0.
* ``<!-- check: stdin TEXT -->`` answers a prompt with ``TEXT``.
* ``<!-- check: contains -->`` lets the output hold more than the next block.
* ``<!-- check: demo -->`` needs demo.plone.org, which changes under other
  visitors: only the exit code counts, and the block runs only with ``--demo``.

``--update`` rewrites the output blocks with what the commands printed, which
is how transcripts get into a page.
"""

from dataclasses import dataclass
from dataclasses import field
from pathlib import Path

import argparse
import os
import re
import shlex
import subprocess
import sys
import tempfile


ROOT = Path(__file__).parents[2]
DOCS = ROOT / "docs"
HERE = Path(__file__).parent
FENCE = re.compile(r"^(\s*)(`{3,})([\w-]+)\s*$")
COMMENT = re.compile(r"^\s*<!-- check: (.+?) -->\s*$")
RUNNERS = ("shell", "python")
OUTPUTS = ("json", "text", "console")
PLONE_PORT = os.environ.get("PLONE_PORT", "8080")
VOLTO_PORT = os.environ.get("VOLTO_PORT", "3000")
PROJECT = os.environ.get("COMPOSE_PROJECT_NAME", "plone-client-docs")
NORMALIZE = [
    (re.compile(r"\b[0-9a-f]{32}\b"), "<UID>"),
    (re.compile(r"\b[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}\b"), "<UUID>"),
    (re.compile(r"\beyJ[\w-]+\.[\w-]+\.[\w-]+"), "<TOKEN>"),
    (re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}[\d.:+Z-]*"), "<DATE>"),
    (re.compile(r'("plone_version": )"[^"]+"'), r'\1"<VERSION>"'),
    (re.compile(r'("time": )[\d.]+'), r"\1<TIME>"),
    (re.compile(r"plone-client/\d[\w.]*"), "plone-client/<VERSION>"),
    (re.compile(r"/(private/)?(var|tmp)/[^\s\"']*/check-[^\s\"'/]*"), "<TMP>"),
]


@dataclass
class Block:
    """One fenced block of a page."""

    start: int
    end: int
    indent: str
    language: str
    text: str
    marks: list[str] = field(default_factory=list)
    output: "Block | None" = None


def normalize(text: str) -> str:
    """Remove what changes from one run to the next.

    :param text: Output or an expected block.
    :returns: The text with placeholders, and no trailing spaces.
    """
    for pattern, replacement in NORMALIZE:
        text = pattern.sub(replacement, text)
    return "\n".join(line.rstrip() for line in text.strip().splitlines())


def to_site(text: str) -> str:
    """Point a block at the ports of this run.

    :param text: Text as written in a page.
    :returns: The text with the ports of this run.
    """
    return text.replace(":8080", f":{PLONE_PORT}").replace(":3000", f":{VOLTO_PORT}")


def to_page(text: str) -> str:
    """Write output with the ports that the pages show.

    :param text: What a command printed.
    :returns: The text with the ports of the documentation.
    """
    return text.replace(f":{PLONE_PORT}", ":8080").replace(f":{VOLTO_PORT}", ":3000")


def parse(path: Path) -> list[Block]:
    """Find the blocks to check in a page.

    :param path: The page.
    :returns: The blocks between the start and stop comments, with their marks.
    """
    lines = path.read_text().splitlines()
    blocks: list[Block] = []
    marks: list[str] = []
    active = False
    last: Block | None = None
    index = 0
    while index < len(lines):
        comment = COMMENT.match(lines[index])
        if comment:
            mark = comment.group(1).strip()
            if mark == "start":
                active = True
            elif mark == "stop":
                active = False
            else:
                marks.append(mark)
            index += 1
            continue
        fence = FENCE.match(lines[index])
        if not fence:
            # Prose between two blocks does not break the pair.
            index += 1
            continue
        indent, ticks, language = fence.groups()
        end = index + 1
        closing = re.compile(rf"^\s*`{{{len(ticks)},}}\s*$")
        while end < len(lines) and not closing.match(lines[end]):
            end += 1
        body = [line.removeprefix(indent) for line in lines[index + 1 : end]]
        if active:
            block = Block(index + 1, end, indent, language, "\n".join(body), marks)
            marks = []
            if language in OUTPUTS and last is not None and not block.marks:
                last.output = block
                last = None
            else:
                blocks.append(block)
                last = block if language in RUNNERS else None
        else:
            marks = []
        index = end + 1
    return blocks


def mark_value(block: Block, name: str) -> str | None:
    """The value of a mark.

    :param block: The block.
    :param name: Name of the mark.
    :returns: Its value, an empty string if it has none, or ``None``.
    """
    for mark in block.marks:
        key, _, value = mark.partition(" ")
        if key == name:
            return value
    return None


def keyring_environment(workdir: Path) -> dict[str, str]:
    """Environment of the commands: everything stays in the temporary directory.

    :param workdir: The temporary directory.
    :returns: The environment.
    """
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("PLONE_CLIENT")
    }
    env.update(
        HOME=str(workdir),
        PATH=f"{ROOT / '.venv/bin'}:{env['PATH']}",
        PLONE_CLIENT_CONFIG=str(workdir / "config.toml"),
        PYTHONPATH=str(HERE),
        PYTHON_KEYRING_BACKEND="file_keyring.FileKeyring",
        CHECK_KEYRING_FILE=str(workdir / "keyring.json"),
    )
    return env


def execute(block: Block, workdir: Path, env: dict[str, str]) -> tuple[int, str]:
    """Run a block; the shell's variables carry over to the next one.

    :param block: The block.
    :param workdir: Directory of the run.
    :param env: Environment.
    :returns: Exit code and combined output.
    """
    code = to_site(block.text)
    if block.language == "python":
        script = workdir / ".block.py"
        script.write_text(code)
        command = ["python", str(script)]
    else:
        state = workdir / ".shell-state"
        state.touch()
        body = f"source {shlex.quote(str(state))}\n{code}\n__code=$?\n"
        body += f"export -p > {shlex.quote(str(state))}\nexit $__code\n"
        command = ["bash", "-c", body]
    answer = mark_value(block, "stdin")
    done = subprocess.run(
        command,
        cwd=workdir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        input="" if answer is None else f"{answer}\n",
        text=True,
        timeout=180,
    )
    return done.returncode, done.stdout.replace(str(workdir), "<TMP>")


def check_page(path: Path, update: bool, demo: bool) -> tuple[int, int, list[str]]:
    """Run one page.

    :param path: The page.
    :param update: Write the output into the page.
    :param demo: Run the blocks that need demo.plone.org.
    :returns: Commands run, outputs compared, and the failures.
    """
    name = path.relative_to(ROOT)
    blocks = parse(path)
    commands, outputs = 0, 0
    failures: list[str] = []
    updates: list[tuple[Block, str]] = []
    with tempfile.TemporaryDirectory(prefix="check-") as directory:
        workdir = Path(directory).resolve()
        env = keyring_environment(workdir)
        for block in blocks:
            where = f"{name}:{block.start}"
            target = mark_value(block, "file") or mark_value(block, "append")
            if mark_value(block, "skip") is not None:
                continue
            if target:
                file = workdir / target
                file.parent.mkdir(parents=True, exist_ok=True)
                mode = "a" if mark_value(block, "append") else "w"
                with file.open(mode) as stream:
                    stream.write(to_site(block.text) + "\n")
                continue
            if block.language not in RUNNERS:
                continue
            is_demo = mark_value(block, "demo") is not None
            if is_demo and not demo:
                continue
            commands += 1
            code, output = execute(block, workdir, env)
            expected = int(mark_value(block, "exit") or 0)
            if code != expected:
                failures.append(f"{where}: exit {code}, expected {expected}\n{output}")
                continue
            if block.output is None or is_demo:
                continue
            outputs += 1
            shown = to_page(output)
            contains = mark_value(block, "contains") is not None
            if update and not contains:
                updates.append((block.output, shown))
                continue
            want, have = normalize(block.output.text), normalize(shown)
            if (want not in have) if contains else (want != have):
                failures.append(
                    f"{where}: output differs\n--- page\n{want}\n--- run\n{have}"
                )
    if updates:
        write_updates(path, updates)
    return commands, outputs, failures


def write_updates(path: Path, updates: list[tuple[Block, str]]) -> None:
    """Replace output blocks, from the end of the page backwards.

    :param path: The page.
    :param updates: Blocks and their new text.
    """
    lines = path.read_text().splitlines()
    for block, text in sorted(updates, key=lambda pair: -pair[0].start):
        body = [
            block.indent + line if line else line for line in text.strip().splitlines()
        ]
        lines[block.start : block.end] = body
    path.write_text("\n".join(lines) + "\n")


def compose(*arguments: str) -> None:
    """Run ``docker compose`` on the site of the checks.

    :param arguments: Its arguments.
    """
    env = {
        **os.environ,
        "SEED_SCRIPT": "/repository/docs/_checks/seed.py",
        "PLONE_PORT": PLONE_PORT,
        "VOLTO_PORT": VOLTO_PORT,
    }
    command = ["docker", "compose", "-p", PROJECT, *arguments]
    subprocess.run(
        command, cwd=ROOT, env=env, check=True, capture_output=True, text=True
    )


def pages(selected: list[str]) -> list[Path]:
    """The pages to run.

    :param selected: Paths relative to ``docs``; every page with checks if empty.
    :returns: The pages.
    """
    if selected:
        return [DOCS / page for page in selected]
    found = sorted(DOCS.rglob("*.md"))
    return [
        page
        for page in found
        if "_build" not in page.parts and "<!-- check: start -->" in page.read_text()
    ]


def main() -> int:
    """Run the checks.

    :returns: The exit code.
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("pages", nargs="*", help="pages, relative to docs/")
    parser.add_argument("--update", action="store_true", help="write the output")
    parser.add_argument("--demo", action="store_true", help="use demo.plone.org")
    parser.add_argument("--keep", action="store_true", help="leave the site running")
    options = parser.parse_args()
    selected = pages(options.pages)
    if not selected:
        print("No page has checks")
        return 1
    failed = False
    for page in selected:
        compose("down", "-v", "--timeout", "2")
        compose("up", "--wait")
        try:
            commands, outputs, failures = check_page(page, options.update, options.demo)
        finally:
            if not options.keep:
                compose("down", "-v", "--timeout", "2")
        relative = page.relative_to(DOCS)
        print(
            f"{relative}: {commands} commands, {outputs} outputs, {len(failures)} failed"
        )
        for failure in failures:
            print(failure)
        failed = failed or bool(failures) or not commands
    print("FAILED" if failed else f"OK: {len(selected)} pages")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
