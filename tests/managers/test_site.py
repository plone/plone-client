from . import check_request

import pytest


CASES = [
    (
        lambda c: c.registry.get("plone.site_title"),
        "GET",
        "/@registry/plone.site_title",
        [],
        None,
    ),
    (
        lambda c: c.registry.update({
            "plone.site_title": "Site",
            "plone.email_from_name": "Site",
        }),
        "PATCH",
        "/@registry",
        [],
        {"plone.site_title": "Site", "plone.email_from_name": "Site"},
    ),
    (
        lambda c: c.registry.set("plone.site_title", "Site"),
        "PATCH",
        "/@registry",
        [],
        {"plone.site_title": "Site"},
    ),
    (lambda c: c.controlpanels.list(), "GET", "/@controlpanels", [], None),
    (
        lambda c: c.controlpanels.get("editing"),
        "GET",
        "/@controlpanels/editing",
        [],
        None,
    ),
    (
        lambda c: c.controlpanels.get("dexterity-types", "Document"),
        "GET",
        "/@controlpanels/dexterity-types/Document",
        [],
        None,
    ),
    (
        lambda c: c.controlpanels.update("editing", {"ext_editor": True}),
        "PATCH",
        "/@controlpanels/editing",
        [],
        {"ext_editor": True},
    ),
    (
        lambda c: c.controlpanels.add("dexterity-types", {"title": "My Type"}),
        "POST",
        "/@controlpanels/dexterity-types",
        [],
        {"title": "My Type"},
    ),
    (
        lambda c: c.controlpanels.delete("dexterity-types", "my_type"),
        "DELETE",
        "/@controlpanels/dexterity-types/my_type",
        [],
        None,
    ),
    (lambda c: c.addons.list(), "GET", "/@addons", [], None),
    (
        lambda c: c.addons.get("plone.session"),
        "GET",
        "/@addons/plone.session",
        [],
        None,
    ),
    (
        lambda c: c.addons.install("plone.session"),
        "POST",
        "/@addons/plone.session/install",
        [],
        None,
    ),
    (
        lambda c: c.addons.uninstall("plone.session"),
        "POST",
        "/@addons/plone.session/uninstall",
        [],
        None,
    ),
    (
        lambda c: c.addons.upgrade("plone.session"),
        "POST",
        "/@addons/plone.session/upgrade",
        [],
        None,
    ),
    (
        lambda c: c.addons.import_profile("plone.restapi", "testing-workflows"),
        "POST",
        "/@addons/plone.restapi/import/testing-workflows",
        [],
        None,
    ),
    (lambda c: c.content_rules.get("/"), "GET", "/@content-rules", [], None),
    (
        lambda c: c.content_rules.assign("/", "rule-1"),
        "POST",
        "/@content-rules/rule-1",
        [],
        None,
    ),
    (
        lambda c: c.content_rules.unassign("/", "rule-1"),
        "DELETE",
        "/@content-rules",
        [],
        {"rule_ids": ["rule-1"]},
    ),
    (
        lambda c: c.content_rules.enable("/", ["rule-1", "rule-2"]),
        "PATCH",
        "/@content-rules",
        [],
        {"form.button.Enable": True, "rule_ids": ["rule-1", "rule-2"]},
    ),
    (
        lambda c: c.content_rules.disable("/", "rule-1"),
        "PATCH",
        "/@content-rules",
        [],
        {"form.button.Disable": True, "rule_ids": ["rule-1"]},
    ),
    (
        lambda c: c.content_rules.apply_to_subfolders("/", "rule-1"),
        "PATCH",
        "/@content-rules",
        [],
        {"form.button.Bubble": True, "rule_ids": ["rule-1"]},
    ),
    (
        lambda c: c.content_rules.apply_to_subfolders("/", "rule-1", apply=False),
        "PATCH",
        "/@content-rules",
        [],
        {"form.button.NoBubble": True, "rule_ids": ["rule-1"]},
    ),
    (
        lambda c: c.content_rules.move("/", "rule-2", up=False),
        "PATCH",
        "/@content-rules",
        [],
        {"operation": "move_down", "rule_id": "rule-2"},
    ),
    (lambda c: c.system.site(), "GET", "/@site", [], None),
    (lambda c: c.system.system(), "GET", "/@system", [], None),
    (lambda c: c.system.database(), "GET", "/@database", [], None),
    (lambda c: c.system.transactions(), "GET", "/@transactions", [], None),
    (
        lambda c: c.system.revert_transactions("QStvcExLS1ZiRlU9"),
        "PATCH",
        "/@transactions",
        [],
        {"transaction_ids": ["QStvcExLS1ZiRlU9"]},
    ),
    (lambda c: c.system.upgrade_info(), "GET", "/@upgrade", [], None),
    (lambda c: c.system.upgrade(), "POST", "/@upgrade", [], {"dry_run": True}),
    (
        lambda c: c.system.upgrade(dry_run=False),
        "POST",
        "/@upgrade",
        [],
        {"dry_run": False},
    ),
    (lambda c: c.system.login_providers(), "GET", "/@login", [], None),
    (
        lambda c: c.system.email_send(
            "jane@example.com", "john@example.com", "Hi", subject="Hello"
        ),
        "POST",
        "/@email-send",
        [],
        {
            "to": "jane@example.com",
            "from": "john@example.com",
            "message": "Hi",
            "subject": "Hello",
        },
    ),
    (
        lambda c: c.system.email_notification("john@example.com", "Hi", name="John"),
        "POST",
        "/@email-notification",
        [],
        {"from": "john@example.com", "message": "Hi", "name": "John"},
    ),
]


@pytest.mark.parametrize("call,method,path,params,body", CASES)
def test_requests(client, site, call, method, path, params, body):
    call(client)
    check_request(site, method, path, params, body)


def test_registry_list(client, site):
    site.add(
        "GET", "/@registry", {"items": [{"name": "plone.site_title", "value": "Site"}]}
    )
    assert list(client.registry.list("site_title")) == [
        {"name": "plone.site_title", "value": "Site"}
    ]
    assert site.params() == [("q", "site_title"), ("b_size", "100")]
