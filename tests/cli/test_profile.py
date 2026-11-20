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


def test_add_with_blocks_setting(invoke, memory_keyring, config_file):
    run = _add(invoke, "blog", "--blocks", '{"codeBlock": true}')
    assert run.exit_code == 0, run.stderr
    profile = load_config(config_file).get("blog")
    assert profile.blocks == {"codeBlock": True}
    run = _add(invoke, "bad", "--blocks", '{"codeBlock": "yes"}')
    assert run.exit_code == 3
    assert "Setting of block type codeBlock" in run.error["message"]


def test_add_with_plate_types(invoke, memory_keyring, config_file, site):
    run = _add(invoke, "wiki", "--plate-type", "WikiPage", "--plate-type", "Note")
    assert run.exit_code == 0, run.stderr
    assert run.json["plate_types"] == ["WikiPage", "Note"]


def test_add_with_transitions(invoke, memory_keyring, config_file, site):
    run = _add(invoke, "blog", "--transition", "submit", "--transition", "retract")
    assert run.exit_code == 0, run.stderr
    assert run.json["transitions"] == ["submit", "retract"]
    run = invoke("workflow", "/news", "publish")
    assert run.exit_code == 7
    assert "allows only these transitions: retract, submit" in run.error["message"]
    assert site.requests == []
    run = invoke("workflow", "/news", "submit")
    assert run.exit_code == 0, run.stderr
    assert site.site_path(site.last) == "/news/@workflow/submit"


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
        "credentials_rejected": False,
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


def test_test_command_reports_rejected_credentials(invoke, memory_keyring, site):
    _add(invoke)
    site.add("GET", "/@actions", {"user": [{"id": "login", "title": "Log in"}]})
    site.add("GET", "/@system", {"type": "Unauthorized", "message": "No"}, status=401)
    run = invoke("profile", "test")
    assert run.exit_code == 4
    assert run.json["credentials_rejected"] is True
    assert "Credentials were rejected" in run.json["message"]
    assert "profile set-secret blog" in run.json["message"]


def test_test_command_anonymous_profile_is_not_a_rejection(invoke, site):
    run = invoke("profile", "add", "anon", "--url", SITE_URL)
    assert run.exit_code == 0, run.stderr
    site.add("GET", "/@actions", {"user": [{"id": "login", "title": "Log in"}]})
    run = invoke("profile", "test")
    assert run.exit_code == 0, run.stderr
    assert run.json["authenticated"] is False
    assert run.json["credentials_rejected"] is False
    assert "message" not in run.json


def test_set_changes_given_settings_only(invoke, memory_keyring, config_file):
    _add(invoke, "intranet", "--description", "Old", "--transition", "submit")
    secret_before = dict(memory_keyring.store)
    run = invoke(
        "profile",
        "set",
        "intranet",
        "description=New text",
        'plate_types:=["WikiPage"]',
        "read_only:=true",
        "url=https://other.example.org/",
    )
    assert run.exit_code == 0, run.stderr
    assert run.json["url"] == "https://other.example.org"
    assert run.json["description"] == "New text"
    assert run.json["plate_types"] == ["WikiPage"]
    assert run.json["read_only"] is True
    assert run.json["transitions"] == ["submit"]
    assert run.json["changed"] == ["description", "plate_types", "read_only", "url"]
    assert memory_keyring.store == secret_before
    profile = load_config(config_file).get("intranet")
    assert profile.username == "editor"
    assert profile.plate_types == ["WikiPage"]
    assert "s3cret" not in config_file.read_text()
    assert load_config(config_file).current == "intranet"


def test_set_json_lists_and_objects(invoke, memory_keyring, config_file):
    _add(invoke, "blog")
    run = invoke(
        "profile",
        "set",
        "blog",
        'transitions:=["submit", "retract"]',
        'blocks:={"codeBlock": true}',
        "timeout:=60",
        "verify:=false",
    )
    assert run.exit_code == 0, run.stderr
    profile = load_config(config_file).get("blog")
    assert profile.transitions == ["submit", "retract"]
    assert profile.blocks == {"codeBlock": True}
    assert profile.timeout == 60.0
    assert profile.verify is False


def test_set_leaves_out_values_equal_to_defaults(invoke, memory_keyring, config_file):
    _add(invoke, "blog")
    invoke("profile", "defaults", "--timeout", "60")
    run = invoke("profile", "set", "blog", "timeout:=60")
    assert run.exit_code == 0, run.stderr
    assert "timeout" not in load_config(config_file).to_mapping()["profiles"]["blog"]
    assert invoke("profile", "show", "blog").json["timeout"] == 60.0
    assert invoke("profile", "set", "blog", "timeout:=90").exit_code == 0
    assert load_config(config_file).get("blog").timeout == 90.0
    assert "timeout" in load_config(config_file).to_mapping()["profiles"]["blog"]


def test_set_refuses_unknown_key_and_keeps_file(invoke, memory_keyring, config_file):
    _add(invoke, "blog")
    text = config_file.read_text()
    run = invoke("profile", "set", "blog", "colour=blue")
    assert run.exit_code == 3
    assert "unknown keys colour" in run.error["message"]
    assert config_file.read_text() == text


def test_set_refuses_invalid_value_and_keeps_file(invoke, memory_keyring, config_file):
    _add(invoke, "blog")
    text = config_file.read_text()
    for assignment, message in (
        ("timeout:=0", "timeout must be positive"),
        ("retries:=-1", "retries must be positive"),
        ("plate_types:=[1]", "plate_types must be a list of type ids"),
        ('blocks:={"codeBlock": "yes"}', "Setting of block type codeBlock"),
        ("verify:=", "Not valid JSON"),
    ):
        run = invoke("profile", "set", "blog", assignment)
        assert run.exit_code == 3, assignment
        assert message in run.error["message"], assignment
        assert config_file.read_text() == text, assignment


def test_set_refuses_value_of_wrong_kind(invoke, memory_keyring, config_file):
    _add(invoke, "blog")
    text = config_file.read_text()
    for assignment, message in (
        ('read_only:="yes"', "read_only must be true or false"),
        ('timeout:="60"', "timeout must be a number"),
        ('transitions:="submit"', "transitions must be a JSON list"),
        ("frontend_url:=5", "frontend_url must be a string"),
    ):
        run = invoke("profile", "set", "blog", assignment)
        assert run.exit_code == 3, assignment
        assert message in run.error["message"], assignment
        assert config_file.read_text() == text, assignment


def test_set_refuses_name_auth_and_secret(invoke, memory_keyring, config_file):
    _add(invoke, "blog")
    text = config_file.read_text()
    secret_before = dict(memory_keyring.store)
    for assignment, message in (
        ("name=other", "cannot be changed"),
        ("auth=token", "Changing the auth"),
        ("secret=env", "Changing where the secret is kept"),
    ):
        run = invoke("profile", "set", "blog", assignment)
        assert run.exit_code == 3, assignment
        assert message in run.error["message"], assignment
        assert config_file.read_text() == text, assignment
    assert memory_keyring.store == secret_before


def test_set_errors(invoke, memory_keyring, config_file):
    _add(invoke, "blog")
    run = invoke("profile", "set", "nope", "read_only:=true")
    assert run.exit_code == 3
    assert "Unknown profile" in run.error["message"]
    run = invoke("profile", "set", "blog", "read_only")
    assert run.exit_code == 3
    assert "Expected key=value or key:=json" in run.error["message"]


def test_unset_returns_setting_to_defaults(invoke, memory_keyring, config_file):
    _add(invoke, "slow", "--timeout", "120", "--description", "Slow one")
    run = invoke("profile", "unset", "slow", "timeout")
    assert run.exit_code == 0, run.stderr
    assert "timeout" not in run.json  # equal to the class default, so left out
    assert run.json["unset"] == ["timeout"]
    assert run.json["description"] == "Slow one"
    profile = load_config(config_file).get("slow")
    assert profile.timeout == 30.0
    assert profile.description == "Slow one"


def test_unset_follows_defaults(invoke, memory_keyring, config_file):
    _add(invoke, "slow", "--timeout", "120")
    invoke("profile", "defaults", "--timeout", "45")
    assert invoke("profile", "unset", "slow", "timeout-x").exit_code == 3
    run = invoke("profile", "unset", "slow", "timeout")
    assert run.exit_code == 0, run.stderr
    assert load_config(config_file).get("slow").timeout == 45.0


def test_unset_refuses_protected_and_unknown_keys(invoke, memory_keyring, config_file):
    _add(invoke, "blog")
    text = config_file.read_text()
    for key, message in (
        ("url", "cannot be unset"),
        ("name", "cannot be changed"),
        ("secret", "Changing where the secret is kept"),
        ("colour", "unknown keys colour"),
    ):
        run = invoke("profile", "unset", "blog", key)
        assert run.exit_code == 3, key
        assert message in run.error["message"], key
        assert config_file.read_text() == text, key
