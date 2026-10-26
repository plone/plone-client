---
myst:
  html_meta:
    "description": "Parameters, constructors, and methods of PloneClient."
    "property=og:description": "Parameters, constructors, and methods of PloneClient."
    "property=og:title": "PloneClient"
---

(reference-client)=

# `PloneClient`

{class}`~plone_client.PloneClient` holds the connection to one Plone site.

## Parameters

<!-- source: src/plone_client/client.py -->

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `url` | `str` | required | URL of the site root, without `++api++`. |
| `username` | `str` | `""` | Login name; empty for anonymous access. |
| `password` | `str` | `""` | Password of `username`. |
| `token` | `str` | `""` | A JWT issued beforehand, sent instead of a password. |
| `auth_method` | `"basic"` or `"jwt"` | `"basic"` | How `username` and `password` authenticate. |
| `auth` | `httpx.Auth` or `None` | `None` | A custom authentication flow; overrides the three above. |
| `api_prefix` | `str` | `"++api++"` | Traversal prefix of the REST API. |
| `timeout` | `float` | `30.0` | Seconds to wait for the site. |
| `verify` | `bool` | `True` | Verify TLS certificates. |
| `retries` | `int` | `3` | Retries of idempotent requests. |
| `backoff` | `float` | `0.5` | Base of the exponential delay between retries, in seconds. |
| `headers` | mapping or `None` | `None` | Extra headers sent with every request. |
| `read_only` | `bool` | `False` | Refuse every request that could change the site. |
| `dry_run` | `bool` | `False` | Record changing requests in `dry_run_log` instead of sending them. |
| `transport` | `httpx.BaseTransport` or `None` | `None` | A custom transport, for tests. |

## Constructors

| Constructor | Reads |
|---|---|
| `PloneClient(url, …)` | The arguments. |
| {meth}`~plone_client.PloneClient.from_env` | `<prefix>URL`, `<prefix>USERNAME` or `<prefix>USER`, `<prefix>PASSWORD`, `<prefix>TOKEN`, `<prefix>AUTH_METHOD`, `<prefix>API_PREFIX`, `<prefix>TIMEOUT`, `<prefix>VERIFY`, `<prefix>READ_ONLY`; the prefix defaults to `PLONE_CLIENT_`. |
| {meth}`~plone_client.PloneClient.from_profile` | A profile from the configuration file, and its secret. |

Keyword arguments passed to either class method win over the settings it reads.

## Retries

<!-- source: src/plone_client/client.py, PloneClient._send -->

| Failure | Requests retried |
|---|---|
| Connection refused or reset before sending | All |
| `429`, `502`, `503`, `504` | `GET`, `HEAD`, `OPTIONS`, `PUT`, `DELETE` |
| Any other status | None |

The delay between retries is `Retry-After` when the site sends it, and `backoff * 2 ** attempt` otherwise.

## Safety switches

| Switch | Changing requests | Reads | Always allowed |
|---|---|---|---|
| `read_only=True` | Raise {class}`~plone_client.exceptions.PloneReadOnlyError` before sending | Sent | `POST` to `@querystring-search`, `@login`, `@login-renew` |
| `dry_run=True` | Recorded in `dry_run_log`; the call returns the record | Sent | Same as above |

## Methods

```{eval-rst}
.. autoclass:: plone_client.PloneClient

.. autofunction:: plone_client.client.encode_params
```

## Related

- {ref}`reference-managers` lists the managers of the client.
- {ref}`howto-connect` shows each way to connect.
