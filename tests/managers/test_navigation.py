from . import check_request

import pytest


CASES = [
    (lambda c: c.navigation.navigation(), "GET", "/@navigation", [], None),
    (
        lambda c: c.navigation.navigation("/news", depth=4),
        "GET",
        "/news/@navigation",
        [("expand.navigation.depth", "4")],
        None,
    ),
    (
        lambda c: c.navigation.breadcrumbs("/news/doc"),
        "GET",
        "/news/doc/@breadcrumbs",
        [],
        None,
    ),
    (
        lambda c: c.navigation.contextnavigation(
            "/news", **{"expand.contextnavigation.bottomLevel": 2}
        ),
        "GET",
        "/news/@contextnavigation",
        [("expand.contextnavigation.bottomLevel", "2")],
        None,
    ),
    (lambda c: c.navigation.navroot("/en/doc"), "GET", "/en/doc/@navroot", [], None),
    (lambda c: c.navigation.actions(), "GET", "/@actions", [], None),
    (
        lambda c: c.navigation.actions("/doc", categories=["object", "user"]),
        "GET",
        "/doc/@actions",
        [("categories:list", "object"), ("categories:list", "user")],
        None,
    ),
    (
        lambda c: c.navigation.inherit(
            "/doc", ["plone.navigationroot", "plone.leadimage"]
        ),
        "GET",
        "/doc/@inherit",
        [("expand.inherit.behaviors", "plone.navigationroot,plone.leadimage")],
        None,
    ),
]


@pytest.mark.parametrize("call,method,path,params,body", CASES)
def test_requests(client, site, call, method, path, params, body):
    call(client)
    check_request(site, method, path, params, body)
