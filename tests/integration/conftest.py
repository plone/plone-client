from . import PASSWORD
from . import USERNAME
from collections.abc import Generator
from pathlib import Path
from plone_client import PloneClient

import httpx
import pytest


@pytest.fixture(scope="session")
def docker_compose_file() -> str:
    """The compose file of the Plone site."""
    return str(Path(__file__).parent / "docker-compose.yml")


def _is_ready(url: str) -> bool:
    try:
        response = httpx.get(
            f"{url}/++api++/@site", auth=(USERNAME, PASSWORD), timeout=5
        )
    except httpx.HTTPError:
        return False
    return response.status_code == 200


@pytest.fixture(scope="session")
def plone_url(docker_ip, docker_services) -> str:
    """URL of the Plone site, once it answers."""
    port = docker_services.port_for("plone", 8080)
    url = f"http://{docker_ip}:{port}/Plone"
    docker_services.wait_until_responsive(
        timeout=180.0, pause=2.0, check=lambda: _is_ready(url)
    )
    return url


@pytest.fixture(params=["basic", "jwt"])
def plone(request, plone_url) -> Generator[PloneClient]:
    """A client of the Plone site, with each authentication method."""
    with PloneClient(
        plone_url, username=USERNAME, password=PASSWORD, auth_method=request.param
    ) as client:
        yield client


@pytest.fixture
def folder(plone) -> Generator[str]:
    """Path of a folder created for the test, removed afterwards."""
    item = plone.content.create("/", "Document", title="Integration")
    path = plone.path(item["@id"])
    yield path
    if plone.exists(path):
        plone.content.delete(path)
