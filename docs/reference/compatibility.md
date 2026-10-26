---
myst:
  html_meta:
    "description": "Which Plone and plone.restapi versions plone-client supports, and which services need a newer plone.restapi."
    "property=og:description": "Which Plone and plone.restapi versions plone-client supports, and which services need a newer plone.restapi."
    "property=og:title": "Compatibility"
    "keywords": "Plone, plone.restapi, compatibility, versions"
---

(reference-compatibility)=

# Compatibility

plone-client talks to a site only through [`plone.restapi`](https://6.docs.plone.org/plone.restapi/).
What a site supports depends on the `plone.restapi` version it runs, not on plone-client.

## Plone and `plone.restapi` versions

<!-- source: https://dist.plone.org/release/<version>/constraints.txt; integration tests in tests/integration -->

| Plone | `plone.restapi` | Status |
|---|---|---|
| 6.2.0 | 10.0.0 | {bdg-success}`Supported` |
| 6.2.2 | 10.0.4 | {bdg-success}`Tested` |
| 6.1.0 | 9.11.0 | {bdg-warning}`Supported, without @inherit` |
| 6.1.5 | 9.15.6 | {bdg-success}`Tested` |
| 6.0.0 | 8.32.6 | {bdg-warning}`Supported, with the gaps listed below` |
| 6.0.15 | 9.13.3 | {bdg-success}`Tested` |
| 5.2 | | {bdg-danger}`Not supported` |

{bdg-success}`Tested`
: The integration test suite runs against the `plone/plone-backend` image of this release.

{bdg-success}`Supported`
: Every service plone-client uses is available.

{bdg-warning}`Supported, with gaps`
: Everything works, except the services in the next table that the site's `plone.restapi` does not have yet.

{bdg-danger}`Not supported`
: plone-client is not tested against it, and nothing is done to keep it working.

## Services that need a newer `plone.restapi`

<!-- source: git history of plone/plone.restapi, src/plone/restapi/services -->

Every service plone-client uses exists in `plone.restapi` 8.32.6, which Plone 6.0.0 ships, except these.
On an older site, the methods below raise {class}`~plone_client.exceptions.PloneNotFoundError`.

| Service | `plone.restapi` | Methods |
|---|---|---|
| `@relations` | 8.39.0 | {class}`client.relations <plone_client.managers.discussion.RelationsManager>` |
| `@site` | 8.40.0 | {meth}`client.system.site() <plone_client.managers.site.SystemManager.site>` |
| `@navroot` | 8.40.0 | {meth}`client.navigation.navroot() <plone_client.managers.navigation.NavigationManager.navroot>` |
| `GET @login` | 9.10.0 | {meth}`client.system.login_providers() <plone_client.managers.site.SystemManager.login_providers>` |
| `@inherit` | 9.13.0 | {meth}`client.navigation.inherit() <plone_client.managers.navigation.NavigationManager.inherit>` |

Logging in with `POST @login` works on every supported version.

## Python

plone-client needs Python 3.11 or later.
The site's own Python version does not matter.

## Related

- {ref}`reference-managers` lists every service each manager calls.
- {ref}`howto-install` installs plone-client.
