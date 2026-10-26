# plone-client

A Python library and a command line client for [Plone](https://plone.org) sites, built on [plone.restapi](https://6.docs.plone.org/plone.restapi/).

- **As a library**, it gives scripts and applications a typed, synchronous client with one manager per REST API service: content, search, workflow, files, users, groups, registry and more.
  Use it to sync content from an external source into Plone, to migrate, or to automate site maintenance.
- **As a command line client**, `plone-client` manages content on any number of Plone sites, each one a named profile whose secret stays in the operating system's keyring.
  It prints JSON and uses stable exit codes, so coding agents and shell scripts can use it in place of an MCP server.

It works with Plone 6.0 and 6.1 and Python 3.11 or later.

## Installation

The library needs only [httpx](https://www.python-httpx.org):

```shell
uv add plone-client
```

The command line client needs the `cli` extra, which adds Typer, keyring and tomlkit:

```shell
uv tool install "plone-client[cli]"
```

## The library

```python
from plone_client import PloneClient
from plone_client import blocks

with PloneClient("https://example.org", username="editor", password="secret") as client:
    post = client.content.create(
        "/blog",
        "Document",
        title="Hello, Plone",
        description="Created with plone-client",
        **blocks.build(blocks.title(), blocks.description(), blocks.text("First post.")),
    )
    client.workflow.transition(post["@id"], "publish")

    for item in client.search.iter("/blog", portal_type="Document", sort_on="created"):
        print(item["@id"], item["review_state"])
```

Paths, full URLs, `uid:<UID>` references and `resolveuid` links are all accepted wherever an item is expected.

### Connecting

```python
client = PloneClient("http://localhost:8080/Plone", username="admin", password="admin")
client = PloneClient(url, username="admin", password="admin", auth_method="jwt")
client = PloneClient(url, token="eyJhbGciOi...")      # a JWT issued beforehand
client = PloneClient.from_env()                       # $PLONE_CLIENT_URL, $PLONE_CLIENT_USERNAME…
client = PloneClient.from_env(prefix="REMOTE_")       # $REMOTE_URL, $REMOTE_USER…
client = PloneClient.from_profile("production")       # a command line profile, secret from the keyring
```

With JWT, the client logs in on the first request and logs in again when the token expires.
Idempotent requests are retried on connection errors and on 429, 502, 503 and 504 responses, honoring `Retry-After`.

Two safety switches make automation easier to trust:

- `read_only=True` refuses every request that could change the site, before it is sent.
- `dry_run=True` records changes in `client.dry_run_log` instead of sending them, while reads still go to the site.

### Managers

| Attribute | Services |
|---|---|
| `content` | content CRUD, `@copy`, `@move`, ordering, `@lock`, `@linkintegrity` |
| `search`, `querystring` | `@search` (with paging), `@querystring`, `@querystring-search` |
| `workflow`, `history`, `working_copy` | `@workflow`, `@history`, `@workingcopy` |
| `files` | base64 and TUS uploads, `@@download`, image scales |
| `navigation` | `@navigation`, `@breadcrumbs`, `@contextnavigation`, `@navroot`, `@actions`, `@inherit` |
| `aliases`, `relations`, `comments`, `translations` | `@aliases`, `@relations`, `@comments`, `@translations` |
| `users`, `groups`, `sharing` | `@users`, `@groups`, `@sharing`, `@principals`, `@roles` |
| `types`, `vocabularies` | `@types`, `@vocabularies` |
| `registry`, `controlpanels`, `addons`, `content_rules`, `system` | site administration |

For a service without a manager, `client.get()`, `post()`, `patch()`, `put()`, `delete()` and `request()` take a path and return the decoded JSON:

```python
client.get("/@my-addon-service", query="value")
```

### Errors

Every error derives from `PloneClientError`.
Errors returned by the site are `PloneAPIError` subclasses named after the status code: `PloneBadRequestError`, `PloneAuthenticationError`, `PloneForbiddenError`, `PloneNotFoundError`, `PloneConflictError` and `PloneServerError`.
Each one carries the status code, the error type and message from plone.restapi, the request method and the URL.

## The command line client

Add a profile per site, then work against the current one or pick another with `-p`:

```shell
plone-client profile add local --url http://localhost:8080/Plone --username admin --use
plone-client profile add prod --url https://example.org --username editor --read-only
plone-client profile list
plone-client profile test prod
```

`profile add` asks for the password and stores it in the keyring: macOS Keychain, Windows Credential Locker or Secret Service on Linux.
A profile can also read its secret from an environment variable (`--secret env`) or from a command such as a password manager's (`--secret command --secret-command "op read op://Private/plone/password"`).
The profiles live in `~/.config/plone-client/config.toml`, and secrets never do.

A `.plone-client.toml` file holding `profile = "blog"` selects a profile for everything run in that directory and below, so each project can point at its own site.

```shell
plone-client ls /blog -f @id,title,review_state
plone-client search -t Document --state private --limit 10
plone-client create /blog Document --title "Hello" -s subjects:='["plone"]' --publish publish
plone-client update /blog/hello -s description="Updated"
plone-client order /blog hello top
plone-client upload /images photo.jpg
plone-client -n delete /blog/hello            # print the request, send nothing
plone-client request GET /@my-addon-service   # any other service
```

Output is JSON on standard output; `-f` keeps only some keys and `-c` prints one line.
Errors are JSON on standard error, with these exit codes:

| Code | Meaning |
|---|---|
| 2 | invalid usage |
| 3 | configuration: unknown profile, missing secret |
| 4 | not authenticated or not allowed |
| 5 | not found |
| 6 | invalid request or conflict |
| 7 | refused by a read-only profile |
| 8 | the site could not be reached |
| 9 | server error |

Commands that delete need `--yes` when standard input is not a terminal.
The [documentation](docs/agents.md) has a ready-made section to paste into a project's `CLAUDE.md` or `AGENTS.md`.

## Development

```shell
make install            # create the environment
make format             # format the code
make lint               # ruff, mypy, pyroma
make test               # unit tests
make test-integration   # integration tests against plone/plone-backend in Docker
make docs               # build the documentation
```

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT.
