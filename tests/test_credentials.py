from plone_client import credentials
from plone_client.exceptions import PloneConfigurationError
from plone_client.profiles import Profile

import pytest
import shlex
import sys


def _profile(**kwargs) -> Profile:
    return Profile(name="site", url="https://example.org", username="editor", **kwargs)


def test_keyring_names():
    assert credentials.keyring_service(_profile()) == "plone-client:site"
    assert credentials.keyring_account(_profile()) == "editor"
    token_profile = Profile(name="t", url="https://example.org", auth="token")
    assert credentials.keyring_account(token_profile) == "token"


def test_keyring_round_trip(memory_keyring):
    profile = _profile()
    with pytest.raises(PloneConfigurationError, match="no secret in the keyring"):
        credentials.get_secret(profile)
    credentials.set_secret(profile, "s3cret")
    assert memory_keyring.store == {("plone-client:site", "editor"): "s3cret"}
    assert credentials.get_secret(profile) == "s3cret"
    assert credentials.delete_secret(profile) is True
    assert credentials.delete_secret(profile) is False


def test_keyring_only_for_keyring_profiles(memory_keyring):
    profile = _profile(secret="env")
    with pytest.raises(PloneConfigurationError, match="not from the keyring"):
        credentials.set_secret(profile, "x")
    assert credentials.delete_secret(profile) is False


def test_env_secret(monkeypatch):
    profile = _profile(secret="env", secret_env="SITE_PW")
    monkeypatch.delenv("SITE_PW", raising=False)
    with pytest.raises(PloneConfigurationError, match=r"set \$SITE_PW"):
        credentials.get_secret(profile)
    monkeypatch.setenv("SITE_PW", "s3cret")
    assert credentials.get_secret(profile) == "s3cret"


def test_command_secret():
    command = f'{shlex.quote(sys.executable)} -c \'print("s3cret"); print("ignored")\''
    profile = _profile(secret="command", secret_command=command)
    assert credentials.get_secret(profile) == "s3cret"


@pytest.mark.parametrize(
    "command",
    [
        f"{shlex.quote(sys.executable)} -c 'import sys; sys.exit(1)'",
        f"{shlex.quote(sys.executable)} -c 'pass'",
        "/nonexistent/secret-tool",
    ],
)
def test_command_secret_failures(command):
    profile = _profile(secret="command", secret_command=command)
    with pytest.raises(PloneConfigurationError, match="secret command"):
        credentials.get_secret(profile)


def test_none_secret():
    assert credentials.get_secret(_profile(secret="none")) == ""
