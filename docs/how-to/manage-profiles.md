---
myst:
  html_meta:
    "description": "Add, test, select, and remove plone-client profiles, and choose where each profile keeps its secret."
    "property=og:description": "Add, test, select, and remove plone-client profiles, and choose where each profile keeps its secret."
    "property=og:title": "Manage profiles"
---

(howto-profiles)=

# Manage profiles

This guide shows you how to keep the connection settings of several sites as profiles, with their secrets outside the configuration file.

## Add a profile

```shell
plone-client profile add local --url http://localhost:8080/Plone --username admin --use
```

`profile add` asks for the password and stores it in the keyring.
`--use` makes the profile the current one.

To refuse every change to a site, add `--read-only`.

```shell
plone-client profile add prod --url https://example.org --username editor --read-only
```

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

```shell
plone-client profile add ci --url https://staging.example.org --username bot \
  --secret env --secret-env STAGING_PASSWORD
```

For a site you read anonymously, leave out `--username` and pass `--secret none`.

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
