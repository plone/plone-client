from .. import SITE_URL
from plone_client.profiles import load_config

import base64
import pytest


pytestmark = pytest.mark.usefixtures("config_file")


def _add(invoke, name="blog", *extra, password="s3cret"):
    return invoke(
        "profile",
        "add",
        name,
        "--url",
        SITE_URL,
        "--username",
        "editor",
        "--password-stdin",
        *extra,
        stdin=f"{password}\n",
    )


def test_add_stores_secret_in_keyring(invoke, memory_keyring, config_file):
    run = _add(invoke, "blog", "--description", "My blog")
    assert run.exit_code == 0, run.stderr
    assert run.json == {
        "name": "blog",
        "url": SITE_URL,
        "username": "editor",
        "description": "My blog",
        "current": True,
    }
    assert memory_keyring.store == {("plone-client:blog", "editor"): "s3cret"}
    text = config_file.read_text()
    assert "s3cret" not in text
    assert load_config(config_file).current == "blog"


def test_add_with_frontend_url(invoke, memory_keyring, config_file):
    run = _add(invoke, "local", "--frontend-url", "http://localhost:3000/")
    assert run.exit_code == 0, run.stderr
    assert run.json["frontend_url"] == "http://localhost:3000"
    profile = load_config(config_file).get("local")
    assert profile.client_settings()["frontend_url"] == "http://localhost:3000"


def test_profile_is_used_for_requests(invoke, memory_keyring, site):
    _add(invoke)
    invoke("get", "/")
    assert (
        site.last.headers["Authorization"]
        == "Basic " + base64.b64encode(b"editor:s3cret").decode()
    )


def test_list_show_use_remove(invoke, memory_keyring):
    _add(invoke, "blog")
    _add(invoke, "prod", "--read-only", password="other")
    listed = invoke("profile", "list").json
    assert [(p["name"], p["current"]) for p in listed] == [
        ("blog", True),
        ("prod", False),
    ]
    assert invoke("profile", "show", "prod").json["read_only"] is True
    assert invoke("profile", "use", "prod").json == {"current": "prod"}
    assert invoke("profile", "show").json["name"] == "prod"
    assert invoke("profile", "remove", "prod").json == {
        "removed": "prod",
        "secret_removed": True,
    }
    assert ("plone-client:prod", "editor") not in memory_keyring.store


def test_read_only_profile_refuses_changes(invoke, memory_keyring, site):
    _add(invoke, "prod", "--read-only")
    run = invoke("update", "/doc", "--title", "x")
    assert run.exit_code == 7
    assert site.requests == []


def test_set_secret(invoke, memory_keyring):
    _add(invoke)
    run = invoke("profile", "set-secret", "blog", "--password-stdin", stdin="changed\n")
    assert run.json == {"name": "blog", "secret": "stored"}
    assert memory_keyring.store[("plone-client:blog", "editor")] == "changed"


def test_add_with_env_secret_does_not_ask(invoke, memory_keyring):
    run = invoke(
        "profile",
        "add",
        "ci",
        "--url",
        SITE_URL,
        "--username",
        "bot",
        "--secret",
        "env",
        "--secret-env",
        "CI_PASSWORD",
    )
    assert run.exit_code == 0, run.stderr
    assert memory_keyring.store == {}


def test_add_duplicate_and_invalid(invoke, memory_keyring):
    _add(invoke)
    run = _add(invoke)
    assert run.exit_code == 3
    assert "already exists" in run.error["message"]
    run = invoke("profile", "add", "bad", "--url", SITE_URL, "--auth", "digest")
    assert run.exit_code == 3
    assert "auth must be one of" in run.error["message"]


def test_add_connection_settings(invoke, memory_keyring):
    run = _add(
        invoke,
        "blog",
        "--timeout",
        "60",
        "--verify",
        "/etc/ssl/ca.pem",
        "--retries",
        "5",
        "--backoff",
        "2",
    )
    assert run.exit_code == 0, run.stderr
    assert {k: run.json[k] for k in ("timeout", "verify", "retries", "backoff")} == {
        "timeout": 60.0,
        "verify": "/etc/ssl/ca.pem",
        "retries": 5,
        "backoff": 2.0,
    }
    assert _add(invoke, "local", "--verify", "no").json["verify"] is False


def test_defaults_command(invoke, memory_keyring, config_file):
    assert invoke("profile", "defaults").json["defaults"] == {}
    run = invoke("profile", "defaults", "--timeout", "60", "--read-only")
    assert run.exit_code == 0, run.stderr
    assert run.json["defaults"] == {"timeout": 60.0, "read_only": True}
    _add(invoke, "blog")
    _add(invoke, "slow", "--timeout", "120")
    assert invoke("profile", "show", "blog").json["timeout"] == 60.0
    assert invoke("profile", "show", "slow").json["timeout"] == 120.0
    assert "timeout" not in load_config(config_file).to_mapping()["profiles"]["blog"]
    run = invoke("profile", "defaults", "--unset", "timeout", "--read-write")
    assert run.json["defaults"] == {"read_only": False}
    assert "timeout" not in invoke("profile", "show", "blog").json


def test_defaults_errors(invoke):
    run = invoke("profile", "defaults", "--unset", "username")
    assert run.exit_code == 3
    assert "unknown keys username" in run.error["message"]
    run = invoke("profile", "defaults", "--retries", "-1")
    assert run.exit_code == 3
    assert "retries must be positive" in run.error["message"]


def test_project_file_selects_profile(invoke, memory_keyring, site, tmp_path):
    _add(invoke, "blog")
    _add(invoke, "other", password="other-pw")
    (tmp_path / ".plone-client.toml").write_text('profile = "other"\n')
    invoke("get", "/")
    assert (
        site.last.headers["Authorization"]
        == "Basic " + base64.b64encode(b"editor:other-pw").decode()
    )


def test_no_profile_configured(invoke):
    run = invoke("get", "/")
    assert run.exit_code == 3
    assert "No profile selected" in run.error["message"]


def test_test_command(invoke, memory_keyring, site):
    _add(invoke)
    site.add("GET", "/@actions", {"user": [{"id": "logout", "title": "Log out"}]})
    site.add("GET", "/@system", {"plone_version": "6.1.5"})
    run = invoke("profile", "test")
    assert run.json == {
        "profile": "blog",
        "url": SITE_URL,
        "authenticated": True,
        "username": "editor",
        "read_only": False,
        "plone_version": "6.1.5",
    }


def test_test_command_with_wrong_credentials(invoke, memory_keyring, site):
    _add(invoke)
    site.add("GET", "/@actions", {"user": [{"id": "login", "title": "Log in"}]})
    site.add("GET", "/@system", {"type": "Unauthorized", "message": "No"}, status=401)
    run = invoke("profile", "test")
    assert run.json["authenticated"] is False
    assert run.json["username"] is None
    assert run.json["plone_version"] is None


def test_group_commands(invoke, memory_keyring, config_file):
    _add(invoke, "blog")
    _add(invoke, "docs")
    assert invoke("profile", "group-set", "sites", "docs", "blog").json == {
        "name": "sites",
        "profiles": ["docs", "blog"],
    }
    assert invoke("profile", "groups").json == [
        {"name": "sites", "profiles": ["docs", "blog"]}
    ]
    assert load_config(config_file).groups == {"sites": ["docs", "blog"]}
    assert invoke("profile", "group-remove", "sites").json == {
        "removed": "sites",
        "profiles": ["docs", "blog"],
    }
    assert invoke("profile", "groups").json == []


def test_group_set_unknown_profile(invoke, memory_keyring):
    _add(invoke, "blog")
    run = invoke("profile", "group-set", "sites", "blog", "nope")
    assert run.exit_code == 3
    assert "unknown profiles nope" in run.error["message"]
