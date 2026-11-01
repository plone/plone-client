---
myst:
  html_meta:
    "description": "Create users and groups on a Plone site, and give them access to content, from Python or the command line."
    "property=og:description": "Create users and groups on a Plone site, and give them access to content, from Python or the command line."
    "property=og:title": "Manage users and sharing"
---

(howto-users-sharing)=

# Manage users and sharing

This guide shows you how to create users and groups on a {term}`Plone` site, and how to give them access to one {term}`content item`.
You need a user with the `Manager` role.
The examples run on the sample content of {ref}`howto-run-a-site`, in Python and on the command line.

<!-- check: start -->

The command line examples read the site from the environment.

```shell
export PLONE_CLIENT_URL=http://localhost:8080/Plone
export PLONE_CLIENT_USERNAME=admin
export PLONE_CLIENT_PASSWORD=admin
```

## Create a user

By default, the command line asks the site to email the user a link to set a password, which needs a mail server.
On a site without one, set the password yourself, as these examples do.

::::{tab-set}
:sync-group: interface

:::{tab-item} Python
:sync: python

```python
from plone_client import PloneClient

client = PloneClient("http://localhost:8080/Plone", username="admin", password="admin")
user = client.users.create(
    "ada",
    email="ada@example.org",
    fullname="Ada Lovelace",
    password="correct-horse-battery",
)
print(user["id"], user["roles"])
```

```text
ada ['Member']
```

:::

:::{tab-item} Command line
:sync: command-line

<!-- check: stdin correct-horse-battery -->
```shell
plone-client users create grace --email grace@example.org --fullname "Grace Hopper" --no-send-reset --password-stdin -f id,roles
```

```json
{
  "id": "grace",
  "roles": [
    "Member"
  ]
}
```

:::

::::

## Add users to a group

A group gives its members a role everywhere on the site.
The sample site has the group `editors`, whose members have the role `Editor`.

::::{tab-set}
:sync-group: interface

:::{tab-item} Python
:sync: python

```python
from plone_client import PloneClient

client = PloneClient("http://localhost:8080/Plone", username="admin", password="admin")
client.groups.create("reviewers-team", title="Reviewers team", roles=["Reviewer"])
client.groups.add_members("reviewers-team", ["ada", "jdoe"])
print(client.groups.get("reviewers-team")["members"]["items"])
print(client.users.get("ada")["roles"])
```

```text
['ada', 'jdoe']
['Member', 'Reviewer']
```

:::

:::{tab-item} Command line
:sync: command-line

```shell
plone-client groups create translators --title "Translators" --role Editor -f id,title
plone-client groups add-member translators grace
plone-client users list --group translators -f id
```

```text
{
  "id": "translators",
  "title": "Translators"
}
{
  "@id": "http://localhost:8080/Plone/++api++/@groups/translators",
  "items": [
    "grace"
  ],
  "items_total": 1
}
[
  {
    "id": "grace"
  }
]
```

:::

::::

## Give access to one item

To give someone access to one item and what is inside it, without a role on the whole site, change its sharing.
The roles you can give are in `available_roles`.
`/about/team` is private, so `ada` cannot read it yet.

::::{tab-set}
:sync-group: interface

:::{tab-item} Python
:sync: python

```python
from plone_client import PloneClient
from plone_client import PloneClientError

url = "http://localhost:8080/Plone"
admin = PloneClient(url, username="admin", password="admin")
ada = PloneClient(url, username="ada", password="correct-horse-battery")

print([role["id"] for role in admin.sharing.get("/about/team")["available_roles"]])
try:
    ada.content.get("/about/team")
except PloneClientError as error:
    print(type(error).__name__)

entry = {"id": "ada", "type": "user", "roles": {"Reader": True}}
admin.sharing.update("/about/team", [entry])
print(ada.content.get("/about/team")["title"])
```

```text
['Contributor', 'Editor', 'Reader', 'Reviewer']
PloneAuthenticationError
Team
```

:::

:::{tab-item} Command line
:sync: command-line

`plone-client sharing` reads the sharing of an item.
No command changes it, so use `request`.

```shell
plone-client request POST /about/team/@sharing -d '{"entries": [{"id": "grace", "type": "user", "roles": {"Reader": true}}]}'
plone-client sharing /about/team --search grace -c | python3 -c 'import json, sys; print([e["roles"]["Reader"] for e in json.load(sys.stdin)["entries"] if e["id"] == "grace"])'
```

```text
{
  "status": 204
}
[True]
```

:::

::::

## Check who has access

{meth}`~plone_client.managers.users.SharingManager.principals` finds users and groups by text, and a user's `roles` and `groups` list what applies to the whole site.

```python
from plone_client import PloneClient

client = PloneClient("http://localhost:8080/Plone", username="admin", password="admin")
found = client.sharing.principals("ada")
print([user["id"] for user in found["users"]])
entries = client.sharing.get("/about/team")["entries"]
print([entry["id"] for entry in entries if any(entry["roles"].values())])
```

```text
['ada']
['ada', 'grace']
```

<!-- check: stop -->

## Related

- {ref}`reference-service-people` lists every call, with its answer.
- {ref}`reference-cli` lists the options of the `users`, `groups`, and `sharing` commands.
- {ref}`howto-handle-errors` shows which error each refusal raises.
