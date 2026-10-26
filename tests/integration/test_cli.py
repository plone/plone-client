from . import PASSWORD
from . import USERNAME
from plone_client.cli import app
from typer.testing import CliRunner

import json
import pytest


pytestmark = pytest.mark.integration


@pytest.fixture
def run(plone_url, tmp_path, monkeypatch):
    """Run the command line against the Plone site, through a profile."""
    monkeypatch.setenv("PLONE_CLIENT_CONFIG", str(tmp_path / "config.toml"))
    monkeypatch.setenv("IT_PASSWORD", PASSWORD)
    monkeypatch.delenv("PLONE_CLIENT_PROFILE", raising=False)
    runner = CliRunner()

    def func(*args):
        result = runner.invoke(app, list(args))
        return result.exit_code, json.loads(result.stdout or result.stderr or "null")

    code, _ = func(
        "profile",
        "add",
        "it",
        "--url",
        plone_url,
        "--username",
        USERNAME,
        "--secret",
        "env",
        "--secret-env",
        "IT_PASSWORD",
        "--use",
    )
    assert code == 0
    return func


def test_info(run):
    code, info = run("info")
    assert code == 0
    assert info["authenticated"] is True


def test_create_publish_search_delete(run):
    code, item = run(
        "create", "/", "Document", "--title", "CLI integration", "--publish", "publish"
    )
    assert code == 0
    assert item["review_state"] == "published"
    code, found = run("search", "-q", "integration", "-f", "@id")
    assert {"@id": item["@id"]} in found
    code, blocks = run("blocks", item["@id"])
    assert [b["@type"] for b in blocks] == ["title", "description"]
    code, result = run("delete", item["@id"], "--yes")
    assert (code, result["dry_run"]) == (0, False)
    code, error = run("get", item["@id"])
    assert (code, error["error"]["type"]) == (5, "NotFound")


def test_read_only(run, plone_url):
    code, error = run("--read-only", "create", "/", "Document", "--title", "No")
    assert (code, error["error"]["type"]) == (7, "PloneReadOnlyError")
