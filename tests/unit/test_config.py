"""Unit tests for PloneClientConfig."""

from __future__ import annotations

from plone_client.config import PloneClientConfig

import pytest


@pytest.mark.unit
class TestPloneClientConfig:
    def test_defaults(self) -> None:
        cfg = PloneClientConfig(base_url="http://localhost:8080/Plone")
        assert cfg.timeout == 30.0
        assert cfg.verify_ssl is True
        assert cfg.max_retries == 3
        assert cfg.retry_backoff == 0.5
        assert cfg.log_level == "WARNING"

    def test_trailing_slash_stripped(self) -> None:
        cfg = PloneClientConfig(base_url="http://localhost:8080/Plone/")
        assert cfg.base_url == "http://localhost:8080/Plone"

    def test_has_credentials(self) -> None:
        cfg = PloneClientConfig(base_url="x", username="u", password="p")
        assert cfg.has_credentials is True

    def test_has_credentials_false_when_incomplete(self) -> None:
        cfg = PloneClientConfig(base_url="x", username="u")
        assert cfg.has_credentials is False

    def test_has_token(self) -> None:
        cfg = PloneClientConfig(base_url="x", token="tok")
        assert cfg.has_token is True

    def test_env_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PLONE_CLIENT_BASE_URL", "http://env.example.com")
        monkeypatch.setenv("PLONE_CLIENT_TIMEOUT", "60")
        monkeypatch.setenv("PLONE_CLIENT_VERIFY_SSL", "false")
        monkeypatch.setenv("PLONE_CLIENT_MAX_RETRIES", "5")
        cfg = PloneClientConfig()
        assert cfg.base_url == "http://env.example.com"
        assert cfg.timeout == 60.0
        assert cfg.verify_ssl is False
        assert cfg.max_retries == 5
