"""
Configuration for plone-client.

All settings can be overridden via environment variables prefixed with
``PLONE_CLIENT_``.  Programmatic values always take precedence.

Environment variables
---------------------
PLONE_CLIENT_BASE_URL
    Base URL of the Plone site (required if not passed to the constructor).
PLONE_CLIENT_USERNAME
    Username for basic / JWT authentication.
PLONE_CLIENT_PASSWORD
    Password for basic / JWT authentication.
PLONE_CLIENT_TOKEN
    Static bearer token (skips the login flow when set).
PLONE_CLIENT_TIMEOUT
    Request timeout in seconds (default: 30).
PLONE_CLIENT_VERIFY_SSL
    Set to ``false`` / ``0`` / ``no`` to disable SSL verification.
PLONE_CLIENT_MAX_RETRIES
    Number of automatic retries on transient errors (default: 3).
PLONE_CLIENT_RETRY_BACKOFF
    Exponential back-off multiplier in seconds (default: 0.5).
PLONE_CLIENT_LOG_LEVEL
    Logging level: DEBUG, INFO, WARNING, ERROR (default: WARNING).
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field

import os


def _bool_env(key: str, default: bool = True) -> bool:
    val = os.environ.get(key, "").strip().lower()
    if not val:
        return default
    return val not in {"false", "0", "no", "off"}


def _int_env(key: str, default: int) -> int:
    val = os.environ.get(key, "").strip()
    try:
        return int(val) if val else default
    except ValueError:
        return default


def _float_env(key: str, default: float) -> float:
    val = os.environ.get(key, "").strip()
    try:
        return float(val) if val else default
    except ValueError:
        return default


@dataclass
class PloneClientConfig:
    """Immutable configuration object for :class:`~plone_client.PloneClient`."""

    # -----------------------------------------------------------------
    # Connection
    # -----------------------------------------------------------------
    base_url: str = field(
        default_factory=lambda: os.environ.get("PLONE_CLIENT_BASE_URL", "")
    )
    """Root URL of the Plone site, e.g. ``https://my.site``."""

    timeout: float = field(
        default_factory=lambda: _float_env("PLONE_CLIENT_TIMEOUT", 30.0)
    )
    """Seconds before a request is aborted."""

    verify_ssl: bool = field(
        default_factory=lambda: _bool_env("PLONE_CLIENT_VERIFY_SSL", True)
    )
    """Whether to verify SSL certificates."""

    # -----------------------------------------------------------------
    # Authentication
    # -----------------------------------------------------------------
    username: str = field(
        default_factory=lambda: os.environ.get("PLONE_CLIENT_USERNAME", "")
    )
    password: str = field(
        default_factory=lambda: os.environ.get("PLONE_CLIENT_PASSWORD", "")
    )
    token: str = field(default_factory=lambda: os.environ.get("PLONE_CLIENT_TOKEN", ""))
    """Pre-issued bearer token.  Skips the JWT login flow when set."""

    # -----------------------------------------------------------------
    # Retry policy
    # -----------------------------------------------------------------
    max_retries: int = field(
        default_factory=lambda: _int_env("PLONE_CLIENT_MAX_RETRIES", 3)
    )
    retry_backoff: float = field(
        default_factory=lambda: _float_env("PLONE_CLIENT_RETRY_BACKOFF", 0.5)
    )
    """
    Multiplier for exponential back-off between retries.

    Sleep duration = ``retry_backoff * (2 ** attempt)``.
    """

    # -----------------------------------------------------------------
    # Advanced networking
    # -----------------------------------------------------------------
    extra_headers: dict[str, str] = field(default_factory=dict)
    """
    Extra HTTP headers added to every request.

    Special value: ``{"X-Request-ID": "auto"}`` generates a fresh UUID4
    per request for distributed tracing.

    Example::

        PloneClientConfig(extra_headers={"X-Request-ID": "auto", "X-App": "myapp"})
    """

    proxies: dict[str, str] = field(default_factory=dict)
    """
    Proxy configuration forwarded to :class:`requests.Session`.

    Example::

        PloneClientConfig(proxies={"https": "http://proxy.corp:8080"})
    """

    # -----------------------------------------------------------------
    # Logging
    # -----------------------------------------------------------------
    log_level: str = field(
        default_factory=lambda: os.environ.get("PLONE_CLIENT_LOG_LEVEL", "WARNING")
    )

    def __post_init__(self) -> None:
        if self.base_url:
            self.base_url = self.base_url.rstrip("/")

    @property
    def has_credentials(self) -> bool:
        return bool(self.username and self.password)

    @property
    def has_token(self) -> bool:
        return bool(self.token)
