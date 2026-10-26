---
myst:
  html_meta:
    "description": "The configuration file, profile settings, project file, and environment variables of plone-client."
    "property=og:description": "The configuration file, profile settings, project file, and environment variables of plone-client."
    "property=og:title": "Configuration"
---

(reference-configuration)=

# Configuration

## Configuration file

<!-- source: src/plone_client/profiles.py -->

Profiles live in a TOML file.
The first of these locations that is set wins.

1. `$PLONE_CLIENT_CONFIG`
2. `$XDG_CONFIG_HOME/plone-client/config.toml`
3. `~/.config/plone-client/config.toml`

```toml
current = "local"

[profiles.local]
url = "http://localhost:8080/Plone"
username = "admin"
auth = "jwt"

[profiles.prod]
url = "https://example.org"
username = "editor"
read_only = true
secret = "command"
secret_command = "op read op://Private/example/password"
```

| Key | Meaning |
|---|---|
| `current` | Name of the profile used when no other one is selected. |
| `profiles.<name>` | One table per profile; see below. |

The file never holds a secret.

## Profile settings

| Key | Type | Default | Meaning |
|---|---|---|---|
| `url` | string | required | URL of the site root. |
| `username` | string | `""` | Login name; empty for anonymous access. |
| `auth` | `basic`, `jwt`, or `token` | `basic` | How the client authenticates; `token` sends the secret as a JWT. |
| `secret` | `keyring`, `env`, `command`, or `none` | `keyring` | Where the secret is kept. |
| `secret_env` | string | `PLONE_CLIENT_PASSWORD` | Variable holding the secret, with `secret = "env"`. |
| `secret_command` | string | `""` | Command printing the secret, with `secret = "command"`; run without a shell. |
| `read_only` | boolean | `false` | Refuse every request that could change the site. |
| `timeout` | number | `30.0` | Seconds to wait for the site. |
| `verify` | boolean | `true` | Verify TLS certificates. |
| `api_prefix` | string | `++api++` | Traversal prefix of the REST API. |
| `description` | string | `""` | Free text, shown by `plone-client profile list`. |

Profile names start with a letter or a digit and contain only letters, digits, `_`, `.`, and `-`.

## Secrets in the keyring

<!-- source: src/plone_client/credentials.py -->

| Field | Value |
|---|---|
| Service | `plone-client:<profile>` |
| Account | The profile's `username`, or `token` for a token profile without one |

The keyring is the operating system's own: macOS Keychain, Windows Credential Locker, or Secret Service on Linux.

## Project file

A `.plone-client.toml` file in the working directory, or in one of its parents, selects the profile for everything run below it.

```toml
profile = "blog"
```

## Profile selection

| Order | Source |
|---|---|
| 1 | `-p`, `--profile`, or the `name` passed to {meth}`~plone_client.PloneClient.from_profile` |
| 2 | `$PLONE_CLIENT_PROFILE` |
| 3 | `.plone-client.toml` |
| 4 | `current` in the configuration file |

The command line skips profiles when given `--url`, or when `$PLONE_CLIENT_URL` is set and no profile was named by `--profile` or `$PLONE_CLIENT_PROFILE`.
It then reads the settings from the environment variables below.

## Environment variables

<!-- source: src/plone_client/profiles.py, settings_from_env -->

{meth}`~plone_client.PloneClient.from_env` reads these variables, with the prefix `PLONE_CLIENT_` unless given another.

| Variable | Meaning |
|---|---|
| `PLONE_CLIENT_URL` | URL of the site root; required. |
| `PLONE_CLIENT_USERNAME` | Login name; `PLONE_CLIENT_USER` is read when it is not set. |
| `PLONE_CLIENT_PASSWORD` | Password. |
| `PLONE_CLIENT_TOKEN` | A JWT issued beforehand. |
| `PLONE_CLIENT_AUTH_METHOD` | `basic` or `jwt`. |
| `PLONE_CLIENT_API_PREFIX` | Traversal prefix of the REST API. |
| `PLONE_CLIENT_TIMEOUT` | Seconds to wait for the site. |
| `PLONE_CLIENT_VERIFY` | `false` to skip TLS verification. |
| `PLONE_CLIENT_READ_ONLY` | `true` to refuse every change. |

These two are read by the command line only.

| Variable | Meaning |
|---|---|
| `PLONE_CLIENT_PROFILE` | Profile to use. |
| `PLONE_CLIENT_CONFIG` | Configuration file. |

## Related

- {ref}`howto-profiles` creates and manages profiles.
- {ref}`explanation-secrets` explains where secrets go and why.
