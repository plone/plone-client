from pathlib import Path
from plone_client.cli.skill import skill_files
from plone_client.cli.skill import skill_text

import pytest
import re


pytestmark = pytest.mark.usefixtures("config_file")


def test_skill_has_frontmatter():
    text = skill_text()
    assert text.startswith("---\nname: plone-client\ndescription: ")
    assert "\n---\n" in text


def test_links_reach_files_of_the_skill():
    links = re.findall(r"\]\((?!http)([^)]+)\)", skill_text())
    assert links == ["references/blocks.md"]
    assert set(links) <= set(skill_files())


def test_show_a_reference(invoke):
    run = invoke("skill", "show", "references/blocks.md")
    assert run.exit_code == 0, run.stderr
    assert run.stdout == skill_text("references/blocks.md")


def test_show_unknown_file(invoke):
    run = invoke("skill", "show", "../secrets.md")
    assert run.exit_code == 2
    assert run.stdout == ""


def test_show(invoke):
    run = invoke("skill", "show")
    assert run.exit_code == 0, run.stderr
    assert run.stdout == skill_text()


def test_install_in_project(invoke, tmp_path):
    run = invoke("skill", "install")
    assert run.exit_code == 0, run.stderr
    target = tmp_path / ".claude/skills/plone-client/SKILL.md"
    assert run.json == {
        "installed": str(Path(".claude/skills/plone-client/SKILL.md")),
        "replaced": False,
    }
    assert target.read_text() == skill_text()
    target.write_text("old")
    assert invoke("skill", "install").json["replaced"] is True
    assert target.read_text() == skill_text()


def test_install_for_user(invoke, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    monkeypatch.setenv("USERPROFILE", str(tmp_path / "home"))
    run = invoke("skill", "install", "--user")
    assert run.exit_code == 0, run.stderr
    target = tmp_path / "home/.claude/skills/plone-client/SKILL.md"
    assert run.json["installed"] == str(target)
    assert target.read_text() == skill_text()


def test_install_in_directory(invoke, tmp_path):
    run = invoke("skill", "install", "--dir", str(tmp_path / "agents"))
    assert run.exit_code == 0, run.stderr
    assert (tmp_path / "agents/plone-client/SKILL.md").read_text() == skill_text()


def test_install_writes_every_file(invoke, tmp_path):
    assert invoke("skill", "install").exit_code == 0
    root = tmp_path / ".claude/skills/plone-client"
    for name in skill_files():
        assert (root / name).read_text() == skill_text(name)
    assert (root / "references/blocks.md").exists()
