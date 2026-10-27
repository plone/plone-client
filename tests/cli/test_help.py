from plone_client import cli
from plone_client.cli import app
from plone_client.cli import panels

import io
import pytest
import typer.main


ROOT_PANELS = [
    panels.CONTENT_READ,
    panels.CONTENT_CHANGE,
    panels.CONTENT_FILES,
    panels.SITE,
    panels.ADVANCED,
    panels.CONFIGURATION,
]
GROUP_PANELS = {
    "users": [panels.BROWSE, panels.WRITE],
    "groups": [panels.BROWSE, panels.WRITE, panels.MEMBERSHIP],
    "registry": [panels.BROWSE, panels.WRITE],
    "aliases": [panels.BROWSE, panels.WRITE],
    "profile": [panels.BROWSE, panels.WRITE, panels.CONNECTION],
    "skill": [panels.BROWSE, panels.WRITE],
}


@pytest.fixture(params=["rich", None], ids=["rich", "plain"])
def mode(request, monkeypatch):
    """Render help as Rich panels or as plain text sections."""
    monkeypatch.setattr(app, "rich_markup_mode", request.param)
    return request.param


def heading(panel: str, mode: str | None) -> str:
    """How a panel title appears in the help."""
    return f"─ {panel} ─" if mode else f"\n{panel}:\n"


def row(name: str, mode: str | None) -> str:
    """How a command row starts in the help."""
    return f"│ {name} " if mode else f"\n  {name} "


def test_root_help_lists_panels_in_order(invoke, mode):
    run = invoke("--help")
    assert run.exit_code == 0, run.stderr
    positions = [run.stdout.index(heading(panel, mode)) for panel in ROOT_PANELS]
    assert positions == sorted(positions)


def test_root_help_lists_commands_in_order(invoke, mode):
    stdout = invoke("--help").stdout
    positions = [stdout.index(row(name, mode)) for name in panels.ROOT_ORDER]
    assert positions == sorted(positions)


def test_root_order_covers_every_command():
    group = typer.main.get_command(app)
    assert sorted(group.commands) == sorted(panels.ROOT_ORDER)


@pytest.mark.parametrize("name", ["", *GROUP_PANELS])
def test_every_command_has_a_panel(invoke, mode, name):
    run = invoke(*([name] if name else []), "--help")
    assert run.exit_code == 0, run.stderr
    assert heading("Commands", mode) not in run.stdout


@pytest.mark.parametrize("name,expected", GROUP_PANELS.items())
def test_group_panels(invoke, mode, name, expected):
    run = invoke(name, "--help")
    positions = [run.stdout.index(heading(panel, mode)) for panel in expected]
    assert positions == sorted(positions)


def test_plain_help_draws_no_boxes(invoke, monkeypatch):
    monkeypatch.setattr(app, "rich_markup_mode", None)
    assert not {"╭", "│", "─ "} & set(invoke("--help").stdout)


class Terminal(io.StringIO):
    def isatty(self) -> bool:
        return True


@pytest.mark.parametrize(
    "stream,expected", [(Terminal(), "rich"), (io.StringIO(), None)]
)
def test_help_markup(stream, expected):
    assert cli.help_markup(stream) == expected


def test_main_picks_the_markup(monkeypatch):
    calls = []

    class FakeApp:
        rich_markup_mode = "rich"

        def __call__(self) -> None:
            calls.append(self.rich_markup_mode)

    monkeypatch.setattr(cli, "app", FakeApp())
    monkeypatch.setattr(cli, "help_markup", lambda: None)
    cli.main()
    assert calls == [None]
