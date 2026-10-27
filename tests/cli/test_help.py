from plone_client.cli import app
from plone_client.cli import panels

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
GROUPS = ["users", "groups", "registry", "aliases", "profile", "skill"]


def test_root_help_lists_panels_in_order(invoke):
    run = invoke("--help")
    assert run.exit_code == 0, run.stderr
    positions = [run.stdout.index(f"─ {panel} ─") for panel in ROOT_PANELS]
    assert positions == sorted(positions)


def test_root_help_lists_commands_in_order(invoke):
    stdout = invoke("--help").stdout
    positions = [stdout.index(f"│ {name} ") for name in panels.ROOT_ORDER]
    assert positions == sorted(positions)


def test_root_order_covers_every_command():
    group = typer.main.get_command(app)
    assert sorted(group.commands) == sorted(panels.ROOT_ORDER)


@pytest.mark.parametrize("name", ["", *GROUPS])
def test_every_command_has_a_panel(invoke, name):
    run = invoke(*([name] if name else []), "--help")
    assert run.exit_code == 0, run.stderr
    assert "─ Commands ─" not in run.stdout


@pytest.mark.parametrize(
    "name,expected",
    [
        ("users", [panels.BROWSE, panels.WRITE]),
        ("groups", [panels.BROWSE, panels.WRITE, panels.MEMBERSHIP]),
        ("registry", [panels.BROWSE, panels.WRITE]),
        ("aliases", [panels.BROWSE, panels.WRITE]),
        ("profile", [panels.BROWSE, panels.WRITE, panels.CONNECTION]),
        ("skill", [panels.BROWSE, panels.WRITE]),
    ],
)
def test_group_panels(invoke, name, expected):
    run = invoke(name, "--help")
    positions = [run.stdout.index(f"─ {panel} ─") for panel in expected]
    assert positions == sorted(positions)
