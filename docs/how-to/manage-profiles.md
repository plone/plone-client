---
myst:
  html_meta:
    "description": "Add, test, select, and remove plone-client profiles, and choose where each profile keeps its secret."
    "property=og:description": "Add, test, select, and remove plone-client profiles, and choose where each profile keeps its secret."
    "property=og:title": "Manage profiles"
---

(howto-profiles)=

# Manage profiles

This guide shows you how to keep the connection settings of several sites as {term}`profiles <profile>`, with their secrets outside the configuration file.

## Add a profile

```shell
plone-client profile add local --url http://localhost:8080/Plone --username admin --use
```

`profile add` asks for the password and stores it in the {term}`keyring`.
`--use` makes the profile the current one.

To refuse every change to a site, add `--read-only`.

```shell
plone-client profile add prod --url https://example.org --username editor --read-only
```

To make an existing profile read-only, set `read_only = true` in its table of the configuration file; see {ref}`reference-configuration`.

To pass the password from a script instead of typing it, use `--password-stdin`.

```shell
plone-client profile add ci --url https://staging.example.org --username bot --password-stdin < password.txt
```

## Keep the secret somewhere else

If the secret lives in a password manager, give the command that prints it.
The command runs without a shell.

```shell
plone-client profile add prod --url https://example.org --username editor \
  --secret command --secret-command "op read op://Private/example/password"
```

If the secret arrives as an environment variable, name the variable.
Without `--secret-env`, the variable is `PLONE_CLIENT_PASSWORD`.
It must be set in every shell that uses the profile.

```shell
plone-client profile add ci --url https://staging.example.org --username bot \
  --secret env --secret-env STAGING_PASSWORD
```

For a site you read anonymously, leave out `--username` and pass `--secret none`.

## Log in with a token

On a site where people log in through another provider, such as GitHub, Google, or the organization's own sign-in, you have no Plone password to store.
Log in with a browser, copy the JWT that the site gave the browser, and keep it in a token profile.
On a Volto site, the token is the browser's `auth_token` cookie.

```shell
plone-client profile add intranet --url https://intranet.example.org --auth token
```

`profile add` asks for the token and stores it in the {term}`keyring`.
When the token expires, store a new one with `login`.
It checks the token, stores it, and prints whom it belongs to and when it expires.

```shell
plone-client login intranet
```

```json
{
  "profile": "intranet",
  "url": "https://intranet.example.org",
  "authenticated": true,
  "username": "maria",
  "token_expires": "2026-11-21T09:12:45+00:00",
  "token_subject": "maria",
  "credentials_rejected": false,
  "read_only": false,
  "plone_version": "6.1.5"
}
```

`login` refuses a token that has already expired, and one that is not a JWT unless you pass `--opaque`.
To pass the token from a script, use `--token-stdin`.

The client renews the token with `@login-renew` when it expires within an hour, and writes the new token to the keyring, so the next command starts with it.
Change the margin with `--renew-margin SECONDS` on `profile add`, or `renew_margin` in the configuration file; `0` turns renewal off.
Keep the margin shorter than the time a token lasts on the site, 12 hours by default: with a longer one, every request renews the token.
A token that expired cannot be renewed: run `login` again.

### Log in through the browser

If the site's frontend can hand the token over, `login --browser` saves you copying it.
`volto-authomatic` does once it supports a loopback `return_url`; see [`collective/volto-authomatic#50`](https://github.com/collective/volto-authomatic/issues/50).

```shell
plone-client login intranet --browser
```

The command waits on `127.0.0.1` and prints the URL of the site's `/login` page.
Open it in the browser you log in to the site with, log in as usual, and allow the handoff when the site asks.
To open it in the default browser instead, pass `--open`.
The site then sends the token to the waiting command, which checks and stores it, and prints the same report as above.

For a profile whose `url` is the backend, the page comes from `frontend_url`.
If the browser runs on another machine, the handoff cannot reach the command, so copy the token instead.
The command gives up after `--timeout` seconds, 300 by default, and `--port` chooses the port to wait on.
The MCP server offers the same login as its `login` tool, so an assistant can renew a login that expired; see {ref}`reference-assistant-server-login`.

```{note}
Only a token kept in the keyring is written back.
With `--secret env` or `--secret command`, the renewed token lasts as long as the command or the MCP server that renewed it.
```

## Tune the connection

A slow site needs a longer timeout, and a flaky network more retries.

```shell
plone-client profile add archive --url https://archive.example.org --username editor \
  --timeout 120 --retries 6 --backoff 1
```

If the site's certificate comes from your organization's own certificate authority, give the CA bundle.

```shell
plone-client profile add intranet --url https://intranet.example.org --username editor \
  --verify /etc/ssl/certs/example-ca.pem
```

`--verify false` turns certificate checks off.
Use it only for a local site with a self-signed certificate.

To use the same settings for every profile, set them as defaults.

```shell
plone-client profile defaults --timeout 60 --retries 5
```

Profiles take these values unless they set their own.
Run `profile defaults` without options to see them, and pass `--unset timeout` to remove one.

## Check a profile

```shell
plone-client profile test prod
```

`profile test` logs in and prints the user it connected as.

## Select a profile

To pick a profile for one command, pass `-p`.

```shell
plone-client -p prod ls /news
```

To pick one for everything run in a project, add a `.plone-client.toml` file at the project's root.

```toml
profile = "blog"
```

To change the current profile, run `profile use`.

```shell
plone-client profile use prod
```

## Replace or remove a secret

```shell
plone-client profile set-secret prod
plone-client profile remove old-site
```

`profile remove` deletes the profile and its secret in the keyring.

## Related

- {ref}`reference-configuration` lists every profile setting and the selection order.
- {ref}`explanation-secrets` explains why secrets stay out of the file.
