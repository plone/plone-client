from . import check_request

import pytest


CASES = [
    (lambda c: c.workflow.info("/doc"), "GET", "/doc/@workflow", [], None),
    (
        lambda c: c.workflow.transition("/doc", "publish"),
        "POST",
        "/doc/@workflow/publish",
        [],
        None,
    ),
    (
        lambda c: c.workflow.transition(
            "/folder",
            "publish",
            comment="Publishing",
            effective="2026-01-21T08:00:00",
            expires="2027-01-21T08:00:00",
            include_children=True,
        ),
        "POST",
        "/folder/@workflow/publish",
        [],
        {
            "comment": "Publishing",
            "effective": "2026-01-21T08:00:00",
            "expires": "2027-01-21T08:00:00",
            "include_children": True,
        },
    ),
    (lambda c: c.history.list("/doc"), "GET", "/doc/@history", [], None),
    (lambda c: c.history.get("/doc", 0), "GET", "/doc/@history/0", [], None),
    (
        lambda c: c.history.revert("/doc", 1),
        "PATCH",
        "/doc/@history",
        [],
        {"version": 1},
    ),
    (lambda c: c.working_copy.info("/doc"), "GET", "/doc/@workingcopy", [], None),
    (lambda c: c.working_copy.create("/doc"), "POST", "/doc/@workingcopy", [], None),
    (
        lambda c: c.working_copy.check_in("/copy_of_doc"),
        "PATCH",
        "/copy_of_doc/@workingcopy",
        [],
        None,
    ),
    (
        lambda c: c.working_copy.cancel("/copy_of_doc"),
        "DELETE",
        "/copy_of_doc/@workingcopy",
        [],
        None,
    ),
]


@pytest.mark.parametrize("call,method,path,params,body", CASES)
def test_requests(client, site, call, method, path, params, body):
    call(client)
    check_request(site, method, path, params, body)
