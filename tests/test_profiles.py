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
        "read_only": False,
    }
    assert profile.client_settings() == {**base, **expected}


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
            "PC_READ_ONLY": "yes",
        },
        prefix="PC_",
    )
    assert settings == {
        "url": "https://example.org",
        "username": "editor",
        "password": " pw ",
        "token": "",
        "auth_method": "jwt",
        "api_prefix": "",
        "timeout": 10.0,
        "verify": False,
        "read_only": True,
    }


def test_settings_from_env_errors():
    with pytest.raises(PloneConfigurationError, match="Set PLONE_CLIENT_URL"):
        profiles.settings_from_env({})
    with pytest.raises(PloneConfigurationError, match="TIMEOUT must be a number"):
        profiles.settings_from_env({
            "PLONE_CLIENT_URL": "u",
            "PLONE_CLIENT_TIMEOUT": "x",
        })
