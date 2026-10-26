"""Tests for the managers.

Most tests are tables of calls and of the request each one must send:
method, site path, query parameters and JSON body, as ``plone.restapi``
documents them.
"""

from .. import FakeSite


UID = "0123456789abcdef0123456789abcdef"


def check_request(site: FakeSite, method: str, path: str, params, body) -> None:
    """Assert the last request matches the expected one.

    :param site: The fake site.
    :param method: Expected method.
    :param path: Expected site path.
    :param params: Expected query parameters.
    :param body: Expected JSON body.
    """
    request = site.last
    assert (request.method, site.site_path(request)) == (method, path)
    assert site.params(request) == params
    assert site.body(request) == body
