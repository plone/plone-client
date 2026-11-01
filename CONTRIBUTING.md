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
make docs-vale          # check the documentation's style with Vale
make docs-linkcheck     # check that the links resolve
make docs-generate      # regenerate the tables of commands, tools and resources
make docs-generate-check  # fail when a generated table is out of date
make docs-check         # run the pages against a fresh site in Docker
make docs-services      # regenerate the service examples from a fresh site
make docs-services-check  # fail when a service example no longer matches a site
make docs-livehtml      # rebuild the documentation as you edit it
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
5. Add it to the table in `docs/reference/managers.md`, to `docs/reference/compatibility.md` if it needs a newer `plone.restapi` than Plone 6.0.0 ships, and an example to `docs/_generate/services/`.

## Write documentation

The documentation follows the [Plone documentation style guide](https://6.docs.plone.org/contributing/documentation/index.html) and the [Diátaxis](https://diataxis.fr/) framework: tutorials, how-to guides, reference, and explanation each have their own folder in `docs/`.
Write one sentence per line.

To add a page, give it the frontmatter of its neighbors, add it to the toctree and the card grid of its section's `index.md`, and link each Plone term to `docs/glossary.md` with `{term}` on its first use.

A change that users can see updates the reference, one how-to guide, and the tutorial that covers it, if there is one.

Commands and transcripts are never typed by hand.
A page runs between `<!-- check: start -->` and `<!-- check: stop -->` comments: its `shell` and `python` blocks run in order against a fresh site, and the `json`, `text` or `console` block after each is compared with what it printed.
The docstring of `docs/_checks/run.py` lists every mark, and `make docs-check PAGE=how-to/troubleshoot.md UPDATE=1` writes the output into a page.
`docs/_checks/seed.py` is the only source of sample content.
Tables of commands, tools and resources come from the code, through `docs/_generate/`, into `docs/_generated/`, so run `make docs-generate` after changing them.

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
