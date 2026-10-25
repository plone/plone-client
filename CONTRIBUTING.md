# Contributing to plone-client

Thank you for your interest in contributing!

---

## Setting up a development environment

```bash
git clone https://github.com/yourorg/plone-client
cd plone-client
python3 -m venv .venv
source .venv/bin/activate

# Core + dev tools
make install

# Also install the async extra (httpx)
make install-async
```

---

## Code style

We use **ruff** for linting and formatting:

```bash
make lint   # check
make fmt    # auto-fix
```

Type annotations are required for all public API.  Check with:

```bash
make typecheck
```

---

## Tests

### Unit tests — no Docker, no network

```bash
make test-unit
```

Use `responses` (sync) and `respx` (async) to mock HTTP in unit tests.
Never make real network calls from unit tests.

### Integration tests — Docker required

```bash
make test-integration
```

The suite uses `pytest-docker` to start `plone/plone-backend:6`.
You can override the image:

```bash
PLONE_DOCKER_IMAGE=plone/plone-backend:6.1 make test-integration
```

### Coverage

```bash
make coverage
# then open htmlcov/index.html
```

---

## Adding a new manager

1. Create `src/plone_client/managers/myfeature.py` extending `BaseManager`.
2. Register it in `managers/__init__.py`.
3. Add an attribute in `PloneClient._init_managers()` in `client.py`.
4. Optionally add an async counterpart in `async_client.py`.
5. Write unit tests in `tests/unit/test_managers.py` (or a new file).
6. Document the new manager in `README.md`.

---

## Submitting a pull request

1. Fork the repo and create a feature branch.
2. Write tests — PRs without tests will not be merged.
3. Run `make lint typecheck test-unit` — all must pass.
4. Update `CHANGELOG.md` under `[Unreleased]`.
5. Open a PR with a clear description.

---

## Reporting bugs

Open an issue at https://github.com/yourorg/plone-client/issues.
Include the Plone version, plone.restapi version, and a minimal reproduction.
