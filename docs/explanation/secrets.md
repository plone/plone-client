---
myst:
  html_meta:
    "description": "Why plone-client keeps passwords out of its configuration file, and how profiles find their secrets."
    "property=og:description": "Why plone-client keeps passwords out of its configuration file, and how profiles find their secrets."
    "property=og:title": "About profiles and secrets"
---

(explanation-secrets)=

# About profiles and secrets

Someone who manages several Plone sites ends up with credentials for each of them: a local development site, a staging site, production, a client's intranet.
Profiles give each site a name, so commands and scripts can say which site they mean without repeating its URL and user every time.

## Why secrets stay out of the file

The configuration file holds names, URLs, usernames, and options.
It never holds a password or a token.

A configuration file gets copied, backed up, synced between machines, and pasted into chat to ask for help.
Each of those is harmless for a URL and a disaster for a password.
Keeping secrets elsewhere means the file can travel freely.

## Where secrets go instead

By default, a secret goes into the operating system's keyring: macOS Keychain, Windows Credential Locker, or Secret Service on Linux.
These stores are encrypted, tied to your login, and already trusted with the passwords of your browser and mail client.

Some environments have a better place.
A team that keeps credentials in a password manager can point a profile at the manager's command line, so the secret is read when needed and never stored on disk.
A CI job receives its secrets as environment variables, so a profile can read one from there.

## Why the project file names a profile, not a site

A `.plone-client.toml` file in a project says which profile the project uses, not where the site is.
The project can be shared in a public repository without revealing anything, and each person working on it keeps their own profile, with their own credentials, under the agreed name.

## Why the environment can override profiles

Containers and CI jobs have no keyring and no configuration file.
They configure the client through `PLONE_CLIENT_URL` and its companions.
When those variables are set and no profile is named explicitly, the command line uses them, so the same commands run unchanged on a workstation and in a pipeline.

## Related

- {ref}`howto-profiles` creates and manages profiles.
- {ref}`reference-configuration` lists every setting and the selection order.
