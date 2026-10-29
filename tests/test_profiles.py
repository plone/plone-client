from pathlib import Path
from plone_client import profiles
from plone_client.exceptions import PloneConfigurationError
from plone_client.profiles import Config
from plone_client.profiles import Profile

import pytest
import stat
import sys


@pytest.mark.parametrize(
    "environ,expected",
    [
        ({"PLONE_CLIENT_CONFIG": "/etc/pc.toml"}, "/etc/pc.toml"),
        ({"XDG_CONFIG_HOME": "/xdg"}, "/xdg/plone-client/config.toml"),
    ],
)
def test_default_config_path(environ, expected):
    assert profiles.default_config_path(environ) == Path(expected)


def test_default_config_path_home(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    assert (
        profiles.default_config_path({})
        == tmp_path / ".config/plone-client/config.toml"
    )


@pytest.mark.parametrize(
    "kwargs,message",
    [
        ({"name": "bad name"}, "Invalid profile name"),
        ({"url": ""}, "has no url"),
        ({"auth": "digest"}, "auth must be one of"),
        ({"secret": "vault"}, "secret must be one of"),
        ({"secret": "command"}, "secret_command is required"),
        ({"verify": ""}, "verify must be true, false or a CA bundle path"),
        ({"verify": 1}, "verify must be true, false or a CA bundle path"),
        ({"timeout": 0}, "timeout must be positive"),
        ({"timeout": "60"}, "timeout must be a number"),
        ({"retries": -1}, "retries must be positive"),
        ({"retries": 1.5}, "retries must be a whole number"),
        ({"retries": True}, "retries must be a number"),
        ({"backoff": -0.5}, "backoff must be positive"),
        ({"blocks": ["codeBlock"]}, "blocks setting must be a mapping"),
        ({"blocks": {"codeBlock": "yes"}}, "codeBlock must be true, false"),
    ],
)
def test_profile_validation(kwargs, message):
    settings = {"name": "site", "url": "https://example.org", **kwargs}
    with pytest.raises(PloneConfigurationError, match=message):
        Profile(**settings)


def test_profile_from_mapping_rejects_unknown_keys():
    with pytest.raises(PloneConfigurationError, match="unknown keys password"):
        Profile.from_mapping("site", {"url": "https://example.org", "password": "x"})


def test_profile_to_mapping_omits_defaults():
    profile = Profile(
        name="site", url="https://example.org/", username="editor", read_only=True
    )
    assert profile.url == "https://example.org"
    assert profile.to_mapping() == {
        "url": "https://example.org",
        "username": "editor",
        "read_only": True,
    }


@pytest.mark.parametrize(
    "kwargs,anonymous",
    [
        ({}, True),
        ({"username": "editor"}, False),
        ({"username": "editor", "secret": "none"}, True),
        ({"auth": "token"}, False),
    ],
)
def test_profile_anonymous(kwargs, anonymous):
    assert Profile(name="s", url="https://example.org", **kwargs).anonymous is anonymous


@pytest.mark.parametrize(
    "kwargs,expected",
    [
        ({}, {}),
        (
            {"username": "editor"},
            {"username": "editor", "password": "s3cret", "auth_method": "basic"},
        ),
        (
            {"username": "editor", "auth": "jwt"},
            {"username": "editor", "password": "s3cret", "auth_method": "jwt"},
        ),
        ({"auth": "token"}, {"token": "s3cret"}),
        (
            {"frontend_url": "https://www.example.org/"},
            {"frontend_url": "https://www.example.org"},
        ),
        ({"blocks": {"codeBlock": True}}, {"blocks": {"codeBlock": True}}),
    ],
)
def test_profile_client_settings(monkeypatch, kwargs, expected):
    monkeypatch.setenv("SITE_SECRET", "s3cret")
    profile = Profile(
        name="s",
        url="https://example.org",
        secret="env",
        secret_env="SITE_SECRET",
        **kwargs,
    )
    base = {
        "url": "https://example.org",
        "api_prefix": "++api++",
        "timeout": 30.0,
        "verify": True,
        "retries": 3,
        "backoff": 0.5,
        "read_only": False,
    }
    assert profile.client_settings() == {**base, **expected}


@pytest.mark.parametrize(
    "value,expected",
    [
        ("true", True),
        (" YES ", True),
        ("1", True),
        ("off", False),
        ("0", False),
        ("/etc/ssl/ca.pem", "/etc/ssl/ca.pem"),
        ("~/ca.pem", "~/ca.pem"),
    ],
)
def test_parse_verify(value, expected):
    assert profiles.parse_verify(value) == expected


def test_parse_verify_empty():
    with pytest.raises(PloneConfigurationError, match="verify must be"):
        profiles.parse_verify(" ")


def test_config_defaults_apply_to_profiles(tmp_path):
    config = Config(
        tmp_path / "config.toml",
        {
            "defaults": {"timeout": 60, "retries": 5, "verify": "/etc/ssl/ca.pem"},
            "profiles": {
                "blog": {"url": "https://example.org"},
                "local": {"url": "http://localhost:8080/Plone", "verify": False},
            },
        },
    )
    blog, local = config.get("blog"), config.get("local")
    assert (blog.timeout, blog.retries, blog.verify) == (60, 5, "/etc/ssl/ca.pem")
    assert (local.timeout, local.verify) == (60, False)
    assert config.to_mapping()["profiles"] == {
        "blog": {"url": "https://example.org"},
        "local": {"url": "http://localhost:8080/Plone", "verify": False},
    }


@pytest.mark.parametrize(
    "defaults,message",
    [
        ({"username": "admin"}, "defaults: unknown keys username"),
        ({"timeout": 0}, "defaults: timeout must be positive"),
    ],
)
def test_config_defaults_validation(tmp_path, defaults, message):
    with pytest.raises(PloneConfigurationError, match=message):
        Config(tmp_path / "config.toml", {"defaults": defaults})


def test_config_set_defaults_moves_inherited_values(tmp_path):
    config = Config(
        tmp_path / "config.toml",
        {
            "defaults": {"timeout": 60},
            "profiles": {
                "blog": {"url": "https://example.org"},
                "slow": {"url": "https://slow.example.org", "timeout": 120},
            },
        },
    )
    config.set_defaults({"timeout": 90, "retries": 1})
    assert config.get("blog").timeout == 90
    assert config.get("slow").timeout == 120
    assert config.get("slow").retries == 1
    config.set_defaults({"timeout": None})
    assert config.defaults == {"retries": 1}
    assert config.get("blog").timeout == 30.0
    assert config.to_mapping()["profiles"]["blog"] == {"url": "https://example.org"}


def test_config_add_use_remove(tmp_path):
    config = Config(tmp_path / "config.toml")
    config.add(Profile(name="a", url="https://a.example.org"))
    config.add(Profile(name="b", url="https://b.example.org"))
    assert config.current == "a"
    with pytest.raises(PloneConfigurationError, match="already exists"):
        config.add(Profile(name="a", url="https://other.example.org"))
    config.add(Profile(name="a", url="https://other.example.org"), replace=True)
    assert config.get("a").url == "https://other.example.org"
    config.remove("a")
    assert config.current == ""
    with pytest.raises(PloneConfigurationError, match="Unknown profile 'a'"):
        config.get("a")
    with pytest.raises(PloneConfigurationError, match="No profile selected"):
        config.get("")


def test_config_save_and_load(tmp_path):
    path = tmp_path / "dir" / "config.toml"
    config = Config(path)
    config.add(Profile(name="blog", url="https://example.org", username="editor"))
    config.add(
        Profile(
            name="local",
            url="http://localhost:8080/Plone",
            auth="jwt",
            username="admin",
        )
    )
    config.save()
    if sys.platform != "win32":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600
    text = path.read_text()
    assert "password" not in text
    loaded = profiles.load_config(path)
    assert loaded.current == "blog"
    assert loaded.get("local").auth == "jwt"
    assert loaded.to_mapping() == config.to_mapping()


def test_config_keeps_the_blocks_setting(tmp_path):
    path = tmp_path / "config.toml"
    config = Config(path)
    setting = {"codeBlock": {"style": "light"}, "slateTable": False}
    config.add(Profile(name="docs", url="https://example.org", blocks=setting))
    config.add(Profile(name="blog", url="https://example.org"))
    config.save()
    loaded = profiles.load_config(path)
    assert loaded.get("docs").blocks == setting
    assert loaded.get("blog").blocks == {}
    assert "blocks" not in loaded.get("blog").summary()


def test_load_missing_and_invalid(tmp_path):
    assert profiles.load_config(tmp_path / "missing.toml").profiles == {}
    broken = tmp_path / "broken.toml"
    broken.write_text("current = ")
    with pytest.raises(PloneConfigurationError, match=r"broken\.toml"):
        profiles.load_config(broken)


def test_find_project_profile(tmp_path):
    project = tmp_path / "blog"
    nested = project / "posts" / "2026"
    nested.mkdir(parents=True)
    other = tmp_path / "other"
    other.mkdir()
    (project / ".plone-client.toml").write_text('profile = "blog"\n')
    assert profiles.find_project_profile(nested) == "blog"
    assert profiles.find_project_profile(other) == ""


def test_current_name_precedence(tmp_path):
    config = Config(tmp_path / "config.toml", {"current": "default", "profiles": {}})
    project = tmp_path / "project"
    project.mkdir()
    assert config.current_name({}, project) == "default"
    (project / ".plone-client.toml").write_text('profile = "project"\n')
    assert config.current_name({}, project) == "project"
    assert config.current_name({"PLONE_CLIENT_PROFILE": "env"}, project) == "env"


def test_settings_from_env():
    settings = profiles.settings_from_env(
        {
            "PC_URL": "https://example.org",
            "PC_USERNAME": "editor",
            "PC_PASSWORD": " pw ",
            "PC_AUTH_METHOD": "jwt",
            "PC_API_PREFIX": "",
            "PC_TIMEOUT": "10",
            "PC_VERIFY": "false",
            "PC_RETRIES": "5",
            "PC_BACKOFF": "1.5",
            "PC_READ_ONLY": "yes",
            "PC_FRONTEND_URL": "https://www.example.org",
        },
        prefix="PC_",
    )
    assert settings == {
        "url": "https://example.org",
        "username": "editor",
        "password": " pw ",
        "token": "",
        "frontend_url": "https://www.example.org",
        "auth_method": "jwt",
        "api_prefix": "",
        "timeout": 10.0,
        "verify": False,
        "retries": 5,
        "backoff": 1.5,
        "read_only": True,
    }


def test_settings_from_env_ca_bundle():
    settings = profiles.settings_from_env({
        "PLONE_CLIENT_URL": "u",
        "PLONE_CLIENT_VERIFY": "/etc/ssl/ca.pem",
    })
    assert settings["verify"] == "/etc/ssl/ca.pem"


@pytest.mark.parametrize("name", ["TIMEOUT", "RETRIES", "BACKOFF"])
def test_settings_from_env_numbers(name):
    with pytest.raises(PloneConfigurationError, match=f"{name} must be a number"):
        profiles.settings_from_env({
            "PLONE_CLIENT_URL": "u",
            f"PLONE_CLIENT_{name}": "x",
        })


def test_settings_from_env_errors():
    with pytest.raises(PloneConfigurationError, match="Set PLONE_CLIENT_URL"):
        profiles.settings_from_env({})


def test_settings_from_env_blocks():
    settings = profiles.settings_from_env({
        "PLONE_CLIENT_URL": "u",
        "PLONE_CLIENT_BLOCKS": '{"codeBlock": {"style": "light"}}',
    })
    assert settings["blocks"] == {"codeBlock": {"style": "light"}}


@pytest.mark.parametrize(
    "raw,message",
    [("{codeBlock", "PLONE_CLIENT_BLOCKS: Expecting"), ("[1]", "must be a mapping")],
)
def test_settings_from_env_blocks_errors(raw, message):
    with pytest.raises(PloneConfigurationError, match=message):
        profiles.settings_from_env({
            "PLONE_CLIENT_URL": "u",
            "PLONE_CLIENT_BLOCKS": raw,
        })


def test_config_groups(tmp_path):
    path = tmp_path / "config.toml"
    config = Config(path)
    for name in ("a", "b", "c"):
        config.add(Profile(name=name, url=f"https://{name}.example.org"))
    assert config.set_group("sites", ["b", "a", "b"]) == ["b", "a"]
    assert [p.name for p in config.group("sites")] == ["b", "a"]
    config.set_group("solo", ["a"])
    config.save()
    loaded = profiles.load_config(path)
    assert loaded.groups == {"sites": ["b", "a"], "solo": ["a"]}
    assert loaded.to_mapping() == config.to_mapping()
    # removing a profile drops it from its groups, and empty groups go
    config.remove("a")
    assert config.groups == {"sites": ["b"]}
    assert config.remove_group("sites") == ["b"]
    assert config.groups == {}
    with pytest.raises(PloneConfigurationError, match=r"Unknown group 'x'.*none"):
        config.group("x")


@pytest.mark.parametrize(
    "name,members,message",
    [
        ("bad name", ["a"], "Invalid group name"),
        ("g", "a", "must be a list"),
        ("g", 3, "must be a list"),
        ("g", [], "has no profiles"),
        ("g", ["a", "zz"], "unknown profiles zz"),
    ],
)
def test_config_group_validation(tmp_path, name, members, message):
    config = Config(tmp_path / "config.toml")
    config.add(Profile(name="a", url="https://a.example.org"))
    with pytest.raises(PloneConfigurationError, match=message):
        config.set_group(name, members)


def test_config_groups_must_be_a_table(tmp_path):
    with pytest.raises(PloneConfigurationError, match="groups must be a table"):
        Config(tmp_path / "config.toml", {"groups": ["a"]})
