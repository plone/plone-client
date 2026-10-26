# Contributing to plone-client

Thank you for helping.
plone-client follows the [Plone contributing guidelines](https://6.docs.plone.org/contributing/index.html).

## Set up

You need [uv](https://docs.astral.sh/uv/), and Docker for the integration tests.

```shell
git clone https://github.com/plone/plone-client.git
cd plone-client
make install
```

## Check your change

```shell
make format             # format the code
make lint               # ruff, mypy and pyroma; changes nothing
make test               # unit tests
make test-coverage      # unit tests with a coverage report
make test-integration   # integration tests against plone/plone-backend in Docker
make docs               # build the documentation; warnings are errors
```

Unit tests never touch the network.
They talk to `tests.FakeSite`, an in-memory site behind an httpx `MockTransport`, and the command line tests use `typer.testing.CliRunner` with the same fake site.

Integration tests start `plone/plone-backend` with pytest-docker.
Pick another image with `PLONE_IMAGE`.

```shell
PLONE_IMAGE=plone/plone-backend:6.0 make test-integration
```

## Add a service

1. Add the methods to the manager for the service in `src/plone_client/managers/`, or create a manager that extends `BaseManager`, and attach it in `PloneClient.__init__`.
2. Accept item references through `self._resolve()` or `self._service()`, so paths, URLs and UIDs all work.
3. Add a case to the table in the matching `tests/managers/` module, checking the method, path, query and body sent.
4. If people will want it on the command line, add a command in `src/plone_client/cli/` and a test in `tests/cli/`.
5. Document it in `docs/`.

Docstrings use reStructuredText field lists: `:param:`, `:returns:` and `:raises:`.

## Changelog

Every pull request needs a news fragment in `news/`, which [towncrier](https://towncrier.readthedocs.io) collects at release time.
Name it after the issue, such as `news/42.feature`, or `news/+short-name.feature` when there is none.
The types are `breaking`, `feature`, `bugfix`, `internal`, `documentation` and `tests`.

```text
Added support for the @upgrade service. @your-github-username
```

## Report a bug

Open an issue at <https://github.com/plone/plone-client/issues>, with the versions of plone-client, Plone and plone.restapi, and the smallest example that shows the problem.
