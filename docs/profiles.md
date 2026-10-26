# Profiles and secrets

A profile names a site, a user, and where that user's secret is kept.
Profiles let one machine work with many Plone sites, and both the command line client and {meth}`~plone_client.PloneClient.from_profile` use them.

## Add a profile

```shell
plone-client profile add local --url http://localhost:8080/Plone --username admin --use
plone-client profile add prod --url https://example.org --username editor --read-only
```

`profile add` asks for the password and stores it in the operating system's keyring.
In a script, pipe the password in with `--password-stdin`.
`--use` makes the new profile the current one, and `--read-only` makes the client refuse every change to that site.

Check that a profile works with `profile test`, which logs in and prints the user it connected as.

```shell
plone-client profile test prod
```

## Where profiles are kept

Profiles live in a TOML file.
The first of these locations that is set wins:

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

The file never holds a secret, so it is safe to back up or share.
Each profile also accepts `timeout`, `verify`, `api_prefix` and `description`.

## Where secrets are kept

The `secret` setting of a profile says where its password or token comes from.

`keyring`
: The default.
  The secret is stored with the [keyring](https://pypi.org/project/keyring/) package: macOS Keychain, Windows Credential Locker, or Secret Service on Linux.
  The service name is `plone-client:<profile>` and the account is the username, or `token` for a token profile without one.
  Replace a stored secret with `plone-client profile set-secret <profile>`.

`env`
: The secret is read from the variable named by `secret_env`, `PLONE_CLIENT_PASSWORD` by default.
  Use this in CI, where secrets arrive as variables.

`command`
: The secret is the output of `secret_command`, such as a password manager's command line.
  The command runs without a shell.

`none`
: No secret, for anonymous access.

With `auth = "token"`, the secret is a JWT sent as is, instead of a password.

## Which profile is used

From the strongest choice to the weakest:

1. The name passed with `-p` or `--profile`, or to `from_profile()`.
2. `$PLONE_CLIENT_PROFILE`.
3. A `.plone-client.toml` file in the working directory or one of its parents.
4. The `current` profile of the configuration file.

The project file holds a single setting, so each project can point at its own site.

```toml
profile = "blog"
```

The command line client skips profiles altogether when given `--url`, or when `$PLONE_CLIENT_URL` is set and no profile was named by `--profile` or `$PLONE_CLIENT_PROFILE`.
It then reads the user and the secret from the `PLONE_CLIENT_*` environment variables, which suits CI jobs.
