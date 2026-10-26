---
myst:
  html_meta:
    "description": "Connect plone-client to a Plone site with basic authentication, JWT, a token, environment variables, or a profile."
    "property=og:description": "Connect plone-client to a Plone site with basic authentication, JWT, a token, environment variables, or a profile."
    "property=og:title": "Connect to a site"
---

(howto-connect)=

# Connect to a site

This guide shows you how to create a {class}`~plone_client.PloneClient` for a site, depending on where its credentials come from.
Use the client as a context manager, so its connections close at the end.

## Pass the credentials

```python
from plone_client import PloneClient

with PloneClient("https://example.org", username="editor", password="secret") as client:
    print(client.content.get("/")["title"])
```

Pass the URL of the site root, without `++api++`.
The client sends HTTP basic authentication.

## Log in with JWT

To log in through `@login` and send the token it returns, pass `auth_method="jwt"`.
The client logs in on the first request, and again when the token expires.

```python
client = PloneClient(url, username="editor", password="secret", auth_method="jwt")
```

If you already have a token, pass it instead of the username and password.

```python
client = PloneClient(url, token="eyJhbGciOi")
```

## Read the environment

In CI jobs and containers, the credentials usually arrive as variables.
{meth}`~plone_client.PloneClient.from_env` reads `PLONE_CLIENT_URL`, `PLONE_CLIENT_USERNAME`, `PLONE_CLIENT_PASSWORD`, and the other variables listed in {ref}`reference-configuration`.

```python
client = PloneClient.from_env()
```

If your project already uses other names, pass their prefix.
This reads `REMOTE_URL`, `REMOTE_USER`, and `REMOTE_PASSWORD`.

```python
client = PloneClient.from_env(prefix="REMOTE_")
```

## Use a profile

On a workstation, a profile keeps the password in the operating system's keyring.
Create profiles with the command line, as {ref}`howto-profiles` shows, then read one.

```python
client = PloneClient.from_profile("production")
client = PloneClient.from_profile()  # the project's or the current profile
```

## Override settings

Keyword arguments passed to `from_env()` or `from_profile()` win over the settings they read.

```python
client = PloneClient.from_profile("production", read_only=True, timeout=60)
```

## Related

- {ref}`reference-client` lists every parameter.
- {ref}`howto-preview-changes` makes a client refuse or record changes.
