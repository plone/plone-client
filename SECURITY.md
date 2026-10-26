# Security policy

## Reporting a vulnerability

Do not open a public issue for a security problem.
Report it to the Plone Security Team, as described at <https://plone.org/security/report>.

This covers plone-client itself.
Problems in Plone or plone.restapi go to the same team.

## How plone-client handles secrets

- Profiles never store a secret in the configuration file.
  Secrets live in the operating system's keyring, in an environment variable, or in the output of a command, as each profile chooses.
- `plone-client profile show` and `profile list` never print a secret.
- Secret commands run without a shell.
- With `--password-stdin`, `profile add`, `profile set-secret` and `users create` read the secret from standard input, which keeps it out of the shell history.
