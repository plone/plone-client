---
myst:
  html_meta:
    "description": "Run plone-client without a keyring or a terminal: environment variables, secrets, confirmation, exit codes, and a GitHub Actions job."
    "property=og:description": "Run plone-client without a keyring or a terminal: environment variables, secrets, confirmation, exit codes, and a GitHub Actions job."
    "property=og:title": "Use the command line in scripts and CI"
---

(howto-scripts-ci)=

# Use the command line in scripts and CI

This guide shows you how to run plone-client where there is no {term}`keyring` and no terminal, such as a shell script, a container, or a continuous integration job.

The examples run against the {term}`Compose site`; see {ref}`howto-run-a-site`.

<!-- check: start -->

## Connect with environment variables

Without a {term}`profile`, the command line reads the site from `PLONE_CLIENT_*` variables.

```shell
export PLONE_CLIENT_URL=http://localhost:8080/Plone
export PLONE_CLIENT_USERNAME=admin
export PLONE_CLIENT_PASSWORD=admin
plone-client info -f profile,url,authenticated,username
```

```json
{
  "profile": null,
  "url": "http://localhost:8080/Plone",
  "authenticated": true,
  "username": "admin"
}
```

{ref}`reference-configuration` lists every variable.
A profile named with `-p` or `$PLONE_CLIENT_PROFILE` wins over `$PLONE_CLIENT_URL`.

`--url` and `-u` do the same for one command, and must come before the command name.
The password still comes from `$PLONE_CLIENT_PASSWORD`.

```shell
unset PLONE_CLIENT_URL PLONE_CLIENT_USERNAME
plone-client --url http://localhost:8080/Plone -u admin info -f authenticated,username
```

```json
{
  "authenticated": true,
  "username": "admin"
}
```

## Use a profile without a keyring

A container usually has no keyring.
A profile with the default `--secret keyring` then stops with a traceback, whose last line names the problem, and exit code 1.

<!-- check: skip -->
```shell
echo admin | plone-client profile add ci --url http://plone:8080/Plone --username admin --password-stdin
```

```text
keyring.errors.NoKeyringError: No recommended backend was available. Install a recommended 3rd party backend package; or, install the keyrings.alt package if you want to use the non-recommended backends. See https://pypi.org/project/keyring for details.
```

Keep the secret in a variable instead, with `--secret env`.

```shell
unset PLONE_CLIENT_PASSWORD
plone-client profile add ci --url http://localhost:8080/Plone --username admin --secret env --use -c
```

```json
{"name": "ci", "url": "http://localhost:8080/Plone", "username": "admin", "secret": "env", "current": true}
```

The profile stores the name of the variable, and never its value.
Without the variable, the command stops with exit code 3.

<!-- check: exit 3 -->
```shell
plone-client info
```

```json
{
  "error": {
    "type": "PloneConfigurationError",
    "message": "Profile 'ci': set $PLONE_CLIENT_PASSWORD"
  }
}
```

With the variable, it connects.

```shell
export PLONE_CLIENT_PASSWORD=admin
plone-client info -f profile,authenticated
```

```json
{
  "profile": "ci",
  "authenticated": true
}
```

`--secret-env` picks another variable, and `--secret command` runs a command that prints the secret.
See {ref}`howto-profiles`.

## Pass secrets on standard input

Commands that take a secret read it from standard input with a flag, so it stays out of the process list and the shell history.

```shell
printf '%s' "correct-horse-battery" | plone-client users create robot --email robot@example.org --no-send-reset --password-stdin -f id
```

```json
{
  "id": "robot"
}
```

`profile add`, `profile set-secret`, and `mcp-token set` have the same kind of flag.

## Answer confirmations in advance

{term}`Confirmation` needs a terminal.
Without one, a destructive command refuses to run, and exits with code 2.

<!-- check: exit 2 -->
```shell
plone-client users delete robot
```

```text
Delete user robot: pass --yes to confirm
```

Pass `--yes` when the script has made sure of what it deletes.

```shell
plone-client users delete robot --yes
```

```json
{
  "deleted": "robot",
  "dry_run": false
}
```

## Read the results

`-c` prints each result on one line, which suits `jq` and logs.
Errors go to standard error, so standard output stays clean.

```shell
total=$(plone-client search /news -t "News Item" --count -c | jq .items_total)
echo "$total news items"
```

```text
5 news items
```

## Act on exit codes

Each failure has its own {term}`exit code`.
Retry what can pass on a second try, and stop on the rest.

<!-- check: file check-site.sh -->
```shell
#!/usr/bin/env bash
plone-client info -c > /dev/null
code=$?
case $code in
  0) echo "The site answers." ;;
  3) echo "Fix the configuration." ; exit 1 ;;
  4) echo "Fix the credentials." ; exit 1 ;;
  8 | 9) echo "The site is down: try again later." ; exit 75 ;;
  *) echo "Unexpected exit code $code." ; exit 1 ;;
esac
```

```shell
bash check-site.sh
```

```text
The site answers.
```

## Make a job unable to change a site

For an audit, set `PLONE_CLIENT_READ_ONLY`, so that a mistake in the script cannot change anything.
`$PLONE_CLIENT_URL` also wins over the current profile.

<!-- check: exit 7 -->
```shell
export PLONE_CLIENT_URL=http://localhost:8080/Plone PLONE_CLIENT_USERNAME=admin PLONE_CLIENT_READ_ONLY=true
plone-client delete /news/release-6-2 --yes
```

```json
{
  "error": {
    "type": "PloneReadOnlyError",
    "message": "DELETE /news/release-6-2 refused: the client is read-only"
  }
}
```

## Run an audit in GitHub Actions

This job starts the sample site, and fails if any news item is waiting for review.
To audit a real site, remove the steps that start it, set `PLONE_CLIENT_URL`, and take the password from a repository secret, as in `${{ secrets.PLONE_PASSWORD }}`.

<!-- check: skip -->
```yaml
name: Content audit

on:
  workflow_dispatch:
  schedule:
    - cron: "0 6 * * 1"

jobs:
  audit:
    runs-on: ubuntu-latest
    env:
      PLONE_CLIENT_URL: http://localhost:8080/Plone
      PLONE_CLIENT_USERNAME: admin
      PLONE_CLIENT_PASSWORD: admin
      PLONE_CLIENT_READ_ONLY: "true"
    steps:
      - name: Install uv
        uses: astral-sh/setup-uv@v10.3.2

      - name: Install plone-client
        run: uv tool install "plone-client[cli]"

      - name: Start the sample site
        run: |
          curl -O https://raw.githubusercontent.com/plone/plone-client/main/docker-compose.yml
          docker compose up --wait

      - name: Check the connection
        run: plone-client info

      - name: Fail on items waiting for review
        run: |
          pending=$(plone-client search --state pending --count -c | jq .items_total)
          echo "$pending items waiting for review"
          test "$pending" -eq 0
```

The commands of the last two steps are the same as on your computer.

```shell
pending=$(plone-client search --state pending --count -c | jq .items_total)
echo "$pending items waiting for review"
```

```text
1 items waiting for review
```

<!-- check: stop -->

## Related

- {ref}`reference-cli` lists the exit codes and options.
- {ref}`reference-configuration` lists the environment variables.
- {ref}`howto-everyday` has recipes to run from a job.
- {ref}`howto-troubleshoot` covers a missing keyring and other failures.
