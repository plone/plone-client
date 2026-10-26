from .. import SITE_URL

import httpx
import pytest


pytestmark = pytest.mark.usefixtures("cli_env")


def test_info_without_profile(invoke, site):
    site.add("GET", "/@actions", {"user": [{"id": "logout"}]})
    site.add("GET", "/@system", {"plone_version": "6.1.5"})
    run = invoke("info")
    assert run.json == {
        "profile": None,
        "url": SITE_URL,
        "authenticated": True,
        "username": "admin",
        "read_only": False,
        "plone_version": "6.1.5",
    }


def test_version():
    from plone_client import __version__
    from plone_client.cli import app
    from typer.testing import CliRunner

    result = CliRunner().invoke(app, ["--version"])
    assert result.stdout.strip() == __version__


def test_types(invoke, site):
    site.add(
        "GET",
        "/@types",
        [{"@id": f"{SITE_URL}/@types/Document", "title": "Page", "addable": True}],
    )
    assert invoke("types").json == [
        {"id": "Document", "title": "Page", "addable": True}
    ]
    invoke("types", "Document")
    assert site.site_path(site.last) == "/@types/Document"


def test_vocabulary(invoke, site):
    site.add("GET", "/@vocabularies/v", {"items": [{"token": "a"}, {"token": "b"}]})
    assert invoke("vocabulary", "v", "--limit", "1").json == [{"token": "a"}]


def test_registry(invoke, site):
    site.add("GET", "/@registry/plone.site_title", "Site")
    assert invoke("registry", "get", "plone.site_title").json == "Site"
    run = invoke("registry", "set", "plone.site_title", '"New"')
    assert run.exit_code == 0, run.stderr
    assert site.body(site.requests[-2]) == {"plone.site_title": "New"}
    run = invoke("registry", "set", "plone.site_title", "not json")
    assert run.exit_code == 2


def test_users_and_groups(invoke, site):
    site.add("POST", "/@users", {"id": "noam"})
    invoke("users", "create", "noam", "--email", "noam@example.com", "--role", "Editor")
    assert site.body() == {
        "username": "noam",
        "email": "noam@example.com",
        "roles": ["Editor"],
        "sendPasswordReset": True,
    }
    invoke("users", "create", "ada", "--password-stdin", stdin="s3cret\n")
    assert site.body() == {"username": "ada", "password": "s3cret"}
    run = invoke("users", "create", "ada", "--password-stdin", stdin="\n")
    assert run.exit_code == 3
    site.add("GET", "/@groups/team", {"members": {"items": ["noam"]}})
    run = invoke("groups", "add-member", "team", "noam")
    assert run.json == {"items": ["noam"]}
    assert site.body(site.requests[-2]) == {"users": {"noam": True}}
    assert invoke("users", "delete", "noam").exit_code == 2
    assert invoke("users", "delete", "noam", "--yes").json == {
        "deleted": "noam",
        "dry_run": False,
    }


def test_aliases(invoke, site):
    site.add("GET", "/doc/@aliases", {"items": [{"path": "/old"}]})
    assert invoke("aliases", "add", "/doc", "/old").json == {
        "items": [{"path": "/old"}]
    }
    assert site.body(site.requests[0]) == {"items": [{"path": "/old"}]}


def test_request(invoke, site):
    site.add("GET", "/@video-metadata", {"title": "Video"})
    run = invoke(
        "request",
        "get",
        "/@video-metadata",
        "-P",
        "videoUrl=https://youtu.be/x",
        "-H",
        "X-Test: 1",
    )
    assert run.json == {"title": "Video"}
    assert site.params() == [("videoUrl", "https://youtu.be/x")]
    assert site.last.headers["X-Test"] == "1"
    run = invoke("request", "POST", "/@video-metadata", "-d", '{"videoUrl": "x"}')
    assert site.body() == {"videoUrl": "x"}
    site.add("DELETE", "/thing", status=204)
    assert invoke("request", "DELETE", "/thing").json == {"status": 204}
    site.add_callable(
        "GET", "/robots.txt", lambda request: httpx.Response(200, text="User-agent: *")
    )
    assert invoke("request", "GET", "/robots.txt").stdout.strip() == "User-agent: *"


def test_url_option_overrides_environment(invoke, site, monkeypatch):
    monkeypatch.delenv("PLONE_CLIENT_URL")
    invoke("--url", "http://other.test/site", "-u", "bot", "get", "/")
    assert str(site.last.url) == "http://other.test/site/++api++"
