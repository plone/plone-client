from . import check_request

import pytest


CASES = [
    (lambda c: c.users.list(), "GET", "/@users", [], None),
    (
        lambda c: c.users.list(
            query="no",
            search="avram",
            groups=["Reviewers", "Site Administrators"],
            limit=5,
        ),
        "GET",
        "/@users",
        [
            ("query", "no"),
            ("search", "avram"),
            ("limit", "5"),
            ("groups-filter:list", "Reviewers"),
            ("groups-filter:list", "Site Administrators"),
        ],
        None,
    ),
    (lambda c: c.users.get("noam"), "GET", "/@users/noam", [], None),
    (
        lambda c: c.users.create(
            "noam", {"email": "noam@example.com"}, sendPasswordReset=True
        ),
        "POST",
        "/@users",
        [],
        {"username": "noam", "email": "noam@example.com", "sendPasswordReset": True},
    ),
    (
        lambda c: c.users.update("noam", roles={"Contributor": False}),
        "PATCH",
        "/@users/noam",
        [],
        {"roles": {"Contributor": False}},
    ),
    (
        lambda c: c.users.delete("noam", delete_memberareas=False),
        "DELETE",
        "/@users/noam",
        [("delete_memberareas", "0"), ("delete_localroles", "1")],
        None,
    ),
    (
        lambda c: c.users.reset_password("noam"),
        "POST",
        "/@users/noam/reset-password",
        [],
        None,
    ),
    (
        lambda c: c.users.update_password("noam", "new", old_password="old"),
        "POST",
        "/@users/noam/reset-password",
        [],
        {"new_password": "new", "old_password": "old"},
    ),
    (lambda c: c.users.schema(), "GET", "/@userschema", [], None),
    (
        lambda c: c.users.schema(registration=True),
        "GET",
        "/@userschema/registration",
        [],
        None,
    ),
    (lambda c: c.users.portrait("noam"), "GET", "/@portrait/noam", [], None),
    (lambda c: c.users.portrait(), "GET", "/@portrait", [], None),
    (lambda c: c.groups.list(query="plo"), "GET", "/@groups", [("query", "plo")], None),
    (lambda c: c.groups.get("ploneteam"), "GET", "/@groups/ploneteam", [], None),
    (
        lambda c: c.groups.create("ploneteam", title="Plone Team"),
        "POST",
        "/@groups",
        [],
        {"groupname": "ploneteam", "title": "Plone Team"},
    ),
    (
        lambda c: c.groups.update("ploneteam", {"description": "Team"}),
        "PATCH",
        "/@groups/ploneteam",
        [],
        {"description": "Team"},
    ),
    (lambda c: c.groups.delete("ploneteam"), "DELETE", "/@groups/ploneteam", [], None),
    (
        lambda c: c.groups.add_members("ploneteam", ["a", "b"]),
        "PATCH",
        "/@groups/ploneteam",
        [],
        {"users": {"a": True, "b": True}},
    ),
    (
        lambda c: c.groups.remove_members("ploneteam", "a"),
        "PATCH",
        "/@groups/ploneteam",
        [],
        {"users": {"a": False}},
    ),
    (lambda c: c.sharing.get("/folder"), "GET", "/folder/@sharing", [], None),
    (
        lambda c: c.sharing.get("/folder", search="admin", include_titles=True),
        "GET",
        "/folder/@sharing",
        [("search", "admin"), ("include_titles", "1")],
        None,
    ),
    (
        lambda c: c.sharing.update(
            "/folder",
            [{"id": "AuthenticatedUsers", "type": "user", "roles": {"Reader": True}}],
            inherit=True,
        ),
        "POST",
        "/folder/@sharing",
        [],
        {
            "entries": [
                {"id": "AuthenticatedUsers", "type": "user", "roles": {"Reader": True}}
            ],
            "inherit": True,
        },
    ),
    (
        lambda c: c.sharing.principals("plone"),
        "GET",
        "/@principals",
        [("search", "plone")],
        None,
    ),
    (lambda c: c.sharing.roles(), "GET", "/@roles", [], None),
]


@pytest.mark.parametrize("call,method,path,params,body", CASES)
def test_requests(client, site, call, method, path, params, body):
    call(client)
    check_request(site, method, path, params, body)
