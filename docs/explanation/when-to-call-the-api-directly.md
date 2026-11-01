---
myst:
  html_meta:
    "description": "When to use a manager, a generic request, or plain plone.restapi, and how to translate the plone.restapi documentation into a call."
    "property=og:description": "When to use a manager, a generic request, or plain plone.restapi, and how to translate the plone.restapi documentation into a call."
    "property=og:title": "When to call the API directly"
---

(explanation-direct-api)=

# When to call the API directly

plone-client offers three levels for the same request, and the choice between them is mostly a question of what you want to stop thinking about.
A {term}`manager` method names a task and knows its URL and its parameters.
A generic method such as `client.get` takes a path and leaves the rest to you.
`client.request` returns the raw response.

<!-- check: start -->

```python
from plone_client import PloneClient

client = PloneClient("http://localhost:8080/Plone", username="admin", password="admin")
print(client.workflow.get("/news/release-6-2")["state"]["id"])
print(client.get("/news/release-6-2/@workflow")["state"]["id"])
print(client.request("GET", "/news/release-6-2/@workflow").status_code)
```

```text
published
published
200
```

<!-- check: stop -->

## Start with the manager

The manager is the right default because it hides the details that are easy to get wrong.
`client.search.search("/news", depth=1)` knows that a search on a folder restricts the results to it, which works the same behind a virtual host.
`client.content.update` adds the header that asks for the changed item.
`client.groups.add_members` knows the shape of a body that says `{"users": {"jdoe": true}}`.
{term}`Refs <ref>` work everywhere, so a path, a URL, and a `uid:` are the same to it.

## Go generic when no manager fits

A service that an add-on registers has no manager, and neither does a query parameter a manager has not learned yet.
That is what `client.get`, `post`, `patch`, `put`, and `delete` are for.
Nothing is lost by using them: authentication, retries, errors, `read_only`, and `dry_run` all sit below the managers.

That last point matters most.
Everything that goes through the client goes through the same checks, so a generic `client.post` is refused by a read-only client like any other change.
There is one judgment built in: every `POST` counts as a change, except `@querystring-search`, `@login`, and `@login-renew`.
An add-on service that uses `POST` to read is refused, and a dry run skips it.

## Go raw when the answer is not JSON

`client.request` is for what the decoded body does not tell you: a status code, a header, a body that is an image.
`client.request("GET", path, raise_for_status=False)` also lets you look at an error answer without an exception, which is how {meth}`~plone_client.PloneClient.exists` works.

## Leave the client when it is in the way

A plain HTTP client makes sense when the program has no reason to depend on plone-client, as with a frontend written in another language, or a one-off `curl` command to see what a site answers.
In Python, on a site you manage, it rarely pays off.
You give up the retries and the safety switches, and you write again what {term}`++api++` and batching already solve.
{ref}`howto-migrate` shows what that kind of code looks like, and how little of it remains.

## Read the `plone.restapi` documentation

The documentation of [`plone.restapi`](https://6.docs.plone.org/plone.restapi/docs/source/index.html) describes each service as an HTTP request, and the translation is mechanical.

| In the documentation | In plone-client |
|---|---|
| `GET /Plone/front-page/@workflow` | `client.get("/front-page/@workflow")`: the path starts at the site root. |
| `Accept: application/json` | Nothing: the client sends it. |
| `Authorization` | Nothing: the client's credentials. |
| `?b_size=10` | `client.get(path, b_size=10)` |
| A JSON body | The `data` argument: `client.post(path, {"key": "value"})` |
| `@id` values with a site URL | Usable as paths, as they are. |
| `batching` in the answer | {meth}`~plone_client.PloneClient.iter_items` |

## Related

- {ref}`howto-call-other-services` shows the calls.
- {ref}`reference-services` lists what the managers cover.
- {ref}`reference-client` documents the generic methods.
