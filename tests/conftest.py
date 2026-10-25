"""
Shared pytest fixtures.

The ``plone`` fixture starts a real Plone container via pytest-docker.
It is skipped automatically when Docker is not available.
"""

from __future__ import annotations

from plone_client import PloneClient
from plone_client.config import PloneClientConfig
from plone_client.connection import PloneConnection

import os
import pytest
import requests
import time


# ---------------------------------------------------------------------------
# Unit-test fixtures — no network required
# ---------------------------------------------------------------------------


@pytest.fixture()
def config() -> PloneClientConfig:
    """Minimal configuration pointing at a fake URL."""
    return PloneClientConfig(
        base_url="http://localhost:8080/Plone",
        username="admin",
        password="admin",
        max_retries=0,
        retry_backoff=0,
    )


@pytest.fixture()
def connection(config: PloneClientConfig) -> PloneConnection:
    """A PloneConnection wired up with the unit-test config."""
    return PloneConnection(config)


@pytest.fixture()
def client(config: PloneClientConfig) -> PloneClient:
    """A PloneClient that does NOT auto-login (no open() called)."""
    return PloneClient(config=config)


# ---------------------------------------------------------------------------
# Integration fixtures — requires Docker
# ---------------------------------------------------------------------------

PLONE_IMAGE = os.environ.get("PLONE_DOCKER_IMAGE", "plone/plone-backend:6")
PLONE_URL = "http://localhost:55001/Plone"
PLONE_USERNAME = "admin"
PLONE_PASSWORD = "admin"


@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):  # type: ignore[no-untyped-def]
    """Path to the docker-compose file used by pytest-docker."""
    return str(pytestconfig.rootpath / "tests" / "integration" / "docker-compose.yml")


def _wait_for_plone(url: str, timeout: int = 120) -> bool:
    """Poll *url* until Plone responds or *timeout* seconds elapse."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(
                url,
                headers={"Accept": "application/json"},
                timeout=5,
            )
            if r.status_code < 500:
                return True
        except requests.RequestException:
            pass
        time.sleep(2)
    return False


@pytest.fixture(scope="session")
def plone_service(docker_services):  # type: ignore[no-untyped-def]
    """Start Plone via Docker and wait until it is healthy."""
    docker_services.start("plone")
    assert _wait_for_plone(PLONE_URL), "Plone did not start in time"
    return PLONE_URL


@pytest.fixture()
def integration_client(plone_service: str) -> PloneClient:
    """A logged-in PloneClient against the Dockerised Plone."""
    cfg = PloneClientConfig(
        base_url=plone_service,
        username=PLONE_USERNAME,
        password=PLONE_PASSWORD,
        max_retries=1,
        retry_backoff=0.1,
    )
    with PloneClient(config=cfg) as c:
        yield c
